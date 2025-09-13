"""
Centralized Logging System for Vybe
Provides structured logging with file rotation, level management, and error handling decorators
"""

import logging
import logging.handlers
import os
import sys
import threading
from datetime import datetime
from pathlib import Path
from functools import wraps
from flask import jsonify, request
from .config import Config

class VybeLogger:
    """Centralized logger for Vybe application"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(VybeLogger, cls).__new__(cls)
                    cls._instance._logger = None
                    cls._instance._setup_logger()
        return cls._instance
    
    def _setup_logger(self):
        """Setup the main application logger"""
        # Create logger
        self._logger = logging.getLogger('vybe')
        self._logger.setLevel(getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO))
        
        # Clear existing handlers
        self._logger.handlers.clear()
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Setup console handler with UTF-8 encoding
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        # Force UTF-8 encoding for console output (Python 3.7+)
        try:
            # Type ignore for reconfigure method which may not be recognized by linter
            if hasattr(console_handler.stream, 'reconfigure'):
                console_handler.stream.reconfigure(encoding='utf-8')  # type: ignore
        except (AttributeError, OSError):
            pass
        self._logger.addHandler(console_handler)
        
        # Setup file handler with rotation
        try:
            # Ensure log directory exists
            log_dir = os.path.dirname(Config.LOG_FILE_PATH)
            os.makedirs(log_dir, exist_ok=True)
            
            file_handler = logging.handlers.RotatingFileHandler(
                Config.LOG_FILE_PATH,
                maxBytes=Config.LOG_MAX_BYTES,
                backupCount=Config.LOG_BACKUP_COUNT,
                encoding='utf-8'
            )
            file_handler.setLevel(getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO))
            file_handler.setFormatter(formatter)
            self._logger.addHandler(file_handler)
            
        except Exception as e:
            self._logger.error(f"Failed to setup file logging: {e}")
        
        # Log startup
        self._logger.info(f"Vybe {Config.VERSION} - Logging system initialized")
        self._logger.info(f"Log level: {Config.LOG_LEVEL}")
        self._logger.info(f"Log file: {Config.LOG_FILE_PATH}")
        
        # Initialize simple deduplication cache for noisy API logs
        self._api_log_cache = {}
        self._api_log_window_seconds = 5
    
    def get_logger(self, name=None):
        """Get a logger instance"""
        if name:
            return logging.getLogger(f'vybe.{name}')
        return self._logger
    
    def debug(self, message, **kwargs):
        """Log debug message"""
        self._logger.debug(message, **kwargs)
    
    def info(self, message, **kwargs):
        """Log info message"""
        self._logger.info(message, **kwargs)
    
    def warning(self, message, **kwargs):
        """Log warning message"""
        self._logger.warning(message, **kwargs)
    
    def error(self, message, **kwargs):
        """Log error message"""
        self._logger.error(message, **kwargs)
    
    def critical(self, message, **kwargs):
        """Log critical message"""
        self._logger.critical(message, **kwargs)
    
    def log_exception(self, exception, context=None):
        """
        Log exception with structured context and recovery suggestions
        
        Args:
            exception: The exception that occurred
            context: Additional context information
        """
        error_context = {
            'exception_type': type(exception).__name__,
            'exception_message': str(exception),
            'timestamp': datetime.now().isoformat(),
            'context': context or {}
        }
        
        # Add request context if available
        try:
            from flask import request
            if request:
                error_context['request'] = {
                    'method': request.method,
                    'endpoint': request.endpoint,
                    'url': request.url,
                    'ip': request.remote_addr,
                    'user_agent': request.headers.get('User-Agent', 'Unknown')
                }
        except Exception as e:
            # Silently fail if we can't get request context
            pass
        
        # Log the structured error
        self._logger.error(
            f"Exception: {error_context['exception_type']}: {error_context['exception_message']}",
            extra={'error_context': error_context}
        )
        
        # Suggest recovery actions based on exception type
        recovery_suggestions = self._get_recovery_suggestions(exception)
        if recovery_suggestions:
            self._logger.info(f"Recovery suggestions: {recovery_suggestions}")
        
        return error_context
    
    def _get_recovery_suggestions(self, exception):
        """
        Get recovery suggestions based on exception type
        
        Args:
            exception: The exception that occurred
            
        Returns:
            List of recovery suggestions
        """
        suggestions = []
        exception_type = type(exception).__name__
        
        # Database-related errors
        if 'Database' in exception_type or 'SQL' in exception_type:
            suggestions.extend([
                "Check database connection and credentials",
                "Verify database schema and migrations",
                "Check for database locks or deadlocks"
            ])
        
        # File system errors
        elif 'FileNotFound' in exception_type or 'Permission' in exception_type:
            suggestions.extend([
                "Verify file paths and permissions",
                "Check disk space availability",
                "Ensure proper file ownership"
            ])
        
        # Network-related errors
        elif 'Connection' in exception_type or 'Timeout' in exception_type:
            suggestions.extend([
                "Check network connectivity",
                "Verify service endpoints and ports",
                "Check firewall and proxy settings"
            ])
        
        # Memory-related errors
        elif 'Memory' in exception_type or 'OutOfMemory' in exception_type:
            suggestions.extend([
                "Check available system memory",
                "Consider reducing model size or batch processing",
                "Monitor memory usage patterns"
            ])
        
        # Configuration errors
        elif 'Config' in exception_type or 'Setting' in exception_type:
            suggestions.extend([
                "Verify configuration files and environment variables",
                "Check for missing required settings",
                "Validate configuration format and values"
            ])
        
        return suggestions
    
    def log_user_action(self, user_id, action, details=None):
        """Log user actions for auditing"""
        message = f"User {user_id} - {action}"
        if details:
            message += f" - {details}"
        self._logger.info(message)
    
    def log_api_request(self, endpoint, method, user_id=None, ip_address=None):
        """Log API requests"""
        message = f"API {method} {endpoint}"
        if user_id:
            message += f" - User: {user_id}"
        if ip_address:
            message += f" - IP: {ip_address}"
        
        # Dedupe particularly noisy endpoints within a short window
        try:
            import time
            key = f"{method}:{endpoint}"
            now = time.time()
            window = self._api_log_window_seconds
            # Make orchestrator/status even quieter
            if 'orchestrator/status' in endpoint:
                window = max(window, 10)
            last = self._api_log_cache.get(key, 0)
            if now - last >= window:
                self._api_log_cache[key] = now
                self._logger.info(message)
            else:
                # Skip duplicate log within window
                return
        except Exception:
            self._logger.info(message)
    
    def log_error_with_context(self, error, context=None):
        """Log errors with additional context"""
        message = f"Error: {str(error)}"
        if context:
            message += f" - Context: {context}"
        self._logger.error(message, exc_info=True)
    
    def get_recent_logs(self, lines=100):
        """Get recent log entries"""
        try:
            if os.path.exists(Config.LOG_FILE_PATH):
                with open(Config.LOG_FILE_PATH, 'r', encoding='utf-8') as f:
                    all_lines = f.readlines()
                    return all_lines[-lines:] if len(all_lines) > lines else all_lines
        except Exception as e:
            self._logger.error(f"Error reading log file: {e}")
        return []
    
    def set_log_level(self, level):
        """Change the logging level"""
        try:
            log_level = getattr(logging, level.upper())
            self._logger.setLevel(log_level)
            for handler in self._logger.handlers:
                if isinstance(handler, logging.handlers.RotatingFileHandler):
                    handler.setLevel(log_level)
            self._logger.info(f"Log level changed to {level.upper()}")
        except AttributeError:
            self._logger.error(f"Invalid log level: {level}")

# Global logger instance
logger = VybeLogger()

# Convenience functions
def get_logger(name=None):
    """Get logger instance"""
    return logger.get_logger(name)

def log_info(message, **kwargs):
    """Log info message"""
    logger.info(message, **kwargs)

def log_warning(message, **kwargs):
    """Log warning message"""
    logger.warning(message, **kwargs)

def log_error(message, **kwargs):
    """Log error message"""
    logger.error(message, **kwargs)

def log_debug(message, **kwargs):
    """Log debug message"""
    logger.debug(message, **kwargs)

def log_user_action(user_id, action, details=None):
    """Log user action"""
    logger.log_user_action(user_id, action, details)

def log_api_request(endpoint, method, user_id=None, ip_address=None):
    """Log API request"""
    logger.log_api_request(endpoint, method, user_id, ip_address)

def log_execution_time(func):
    """Decorator to log function execution time"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        import time
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.info(f"Function {func.__name__} executed in {execution_time:.3f}s")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Function {func.__name__} failed after {execution_time:.3f}s: {str(e)}")
            raise
    return wrapper

def handle_api_errors(f):
    """Decorator to handle API errors with structured logging"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            # Log the error with context
            error_context = logger.log_exception(e, {
                'function': f.__name__,
                'args': str(args),
                'kwargs': str(kwargs)
            })
            
            # Return appropriate error response
            return jsonify({
                'success': False,
                'error': 'Internal server error',
                'error_id': error_context.get('timestamp', 'unknown')
            }), 500
    return wrapper

class PerformanceMonitor:
    """Monitor and log performance metrics"""
    
    def __init__(self):
        self.metrics = {}
        self.start_times = {}
    
    def start_timer(self, operation_name):
        """Start timing an operation"""
        import time
        self.start_times[operation_name] = time.time()
    
    def end_timer(self, operation_name, success=True):
        """End timing an operation and log metrics"""
        import time
        if operation_name in self.start_times:
            duration = time.time() - self.start_times[operation_name]
            
            if operation_name not in self.metrics:
                self.metrics[operation_name] = {
                    'count': 0,
                    'total_time': 0,
                    'avg_time': 0,
                    'min_time': float('inf'),
                    'max_time': 0,
                    'success_count': 0,
                    'error_count': 0
                }
            
            metric = self.metrics[operation_name]
            metric['count'] += 1
            metric['total_time'] += duration
            metric['avg_time'] = metric['total_time'] / metric['count']
            metric['min_time'] = min(metric['min_time'], duration)
            metric['max_time'] = max(metric['max_time'], duration)
            
            if success:
                metric['success_count'] += 1
            else:
                metric['error_count'] += 1
            
            # Log slow operations
            if duration > 5.0:  # Log operations taking more than 5 seconds
                logger.warning(f"Slow operation detected: {operation_name} took {duration:.3f}s")
            
            del self.start_times[operation_name]
            return duration
        return 0
    
    def get_metrics(self):
        """Get current performance metrics"""
        return self.metrics.copy()
    
    def reset_metrics(self):
        """Reset all performance metrics"""
        self.metrics.clear()
        self.start_times.clear()

# Global performance monitor
performance_monitor = PerformanceMonitor()

def monitor_performance(operation_name):
    """Decorator to monitor function performance"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            performance_monitor.start_timer(operation_name)
            try:
                result = func(*args, **kwargs)
                performance_monitor.end_timer(operation_name, success=True)
                return result
            except Exception as e:
                performance_monitor.end_timer(operation_name, success=False)
                raise
        return wrapper
    return decorator
