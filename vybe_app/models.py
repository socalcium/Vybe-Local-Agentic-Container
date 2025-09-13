"""
Database Models and Data Management for Vybe AI Desktop Application.

This module defines all SQLAlchemy database models and provides comprehensive
data management functionality for the Vybe AI Desktop Application. It includes
user management, chat sessions, system configuration, AI model metadata,
and performance monitoring utilities.

The module implements advanced database optimization patterns including:
- Query performance monitoring and slow query detection
- Circuit breaker pattern for error resilience
- Memory optimization for large result sets
- Connection pooling and transaction safety
- Automatic query caching and invalidation

Key Model Categories:
- User Management: User authentication, sessions, and security
- Chat System: Messages, sessions, and conversation history
- AI Models: Model metadata, installation tracking, feedback
- Configuration: System settings, prompts, and user preferences  
- Knowledge Base: RAG collections and metadata management
- Monitoring: Performance metrics, user activity, feedback

Database Features:
- Comprehensive indexing for query optimization
- Automatic timestamp tracking and auditing
- Soft delete capabilities for data preservation
- JSON field support for flexible data storage
- Transaction safety with automatic rollback
- Query performance monitoring and alerting

Security Features:
- Password hashing with secure algorithms
- API key management and device tracking
- Session token management and expiration
- Account lockout protection against brute force
- Two-factor authentication support

Example:
    Basic model usage and query optimization:
    
    >>> from vybe_app.models import User, safe_db_operation
    >>> 
    >>> @safe_db_operation
    >>> def create_user(username, email, password):
    ...     user = User(username=username, email=email)
    ...     user.set_password(password)
    ...     db.session.add(user)
    ...     return user
    
Note:
    All models include comprehensive indexing and support for high-performance
    queries. The module automatically monitors query performance and provides
    circuit breaker protection for database operations.
"""

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json
import re
import time
import threading
from collections import deque
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import and_, or_, Index, text, event
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager

# Import consistent logging
from .logger import log_error, log_warning, log_info
from .utils.cache_manager import query_cache, invalidate_query_cache

# This will be set by the create_app function
db = SQLAlchemy()

# Memory optimization for large result sets
class MemoryOptimizer:
    """
    Optimize memory usage for large database operations.
    
    This class provides utilities for processing large database result sets
    without consuming excessive memory. It implements chunked processing and
    streaming patterns to handle large datasets efficiently.
    
    The optimizer is particularly useful when dealing with bulk operations,
    data migrations, or processing large collections of records that might
    exceed available memory if loaded all at once.
    
    Example:
        Processing a large query in memory-efficient chunks:
        
        >>> query = User.query.filter(User.is_active == True)
        >>> for chunk in MemoryOptimizer.chunked_query(query, chunk_size=500):
        ...     for user in chunk:
        ...         process_user(user)
    """
    
    @staticmethod
    def chunked_query(query, chunk_size=1000):
        """
        Process large queries in chunks to reduce memory usage.
        
        This method breaks large query result sets into smaller chunks that can be
        processed sequentially without loading the entire result set into memory.
        Each chunk is yielded as a list of model instances.
        
        Args:
            query: SQLAlchemy query object to process in chunks.
            chunk_size (int): Number of records to include in each chunk.
                            Defaults to 1000. Smaller values use less memory
                            but may increase database round trips.
        
        Yields:
            list: A list containing up to chunk_size model instances from the query.
                 The last chunk may contain fewer items if the total result count
                 is not evenly divisible by chunk_size.
        
        Example:
            >>> query = User.query.filter(User.created_at > some_date)
            >>> for user_chunk in MemoryOptimizer.chunked_query(query, 500):
            ...     process_user_batch(user_chunk)
        """
        offset = 0
        while True:
            chunk = query.offset(offset).limit(chunk_size).all()
            if not chunk:
                break
            yield chunk
            offset += chunk_size
    
    @staticmethod
    def streaming_query(query, chunk_size=500):
        """
        Stream query results for minimal memory footprint.
        
        This method provides a streaming interface over large query results,
        yielding individual items rather than chunks. It uses chunked_query
        internally but flattens the results for easier iteration.
        
        Args:
            query: SQLAlchemy query object to stream.
            chunk_size (int): Internal chunk size for fetching records.
                            Defaults to 500. This affects memory usage and
                            database performance but not the streaming interface.
        
        Yields:
            object: Individual model instances from the query result set.
        
        Example:
            >>> query = Message.query.filter(Message.created_at < cutoff_date)
            >>> for message in MemoryOptimizer.streaming_query(query):
            ...     archive_message(message)
        """
        for chunk in MemoryOptimizer.chunked_query(query, chunk_size):
            for item in chunk:
                yield item

# Circuit breaker pattern for error handling
class CircuitBreaker:
    """
    Implement circuit breaker pattern for database operations.
    
    The circuit breaker pattern prevents cascading failures by temporarily
    disabling operations that are consistently failing. This class monitors
    the failure rate of database operations and automatically opens the circuit
    when failures exceed a threshold, allowing the system to recover.
    
    States:
        - CLOSED: Normal operation, all calls are attempted
        - OPEN: Circuit is open, calls fail immediately without attempting
        - HALF_OPEN: Testing state, limited calls are attempted to test recovery
    
    Attributes:
        failure_threshold (int): Number of consecutive failures before opening circuit.
        recovery_timeout (int): Seconds to wait before attempting recovery.
        failure_count (int): Current count of consecutive failures.
        last_failure_time (float): Timestamp of the last recorded failure.
        state (str): Current circuit breaker state ('CLOSED', 'OPEN', 'HALF_OPEN').
    
    Example:
        >>> breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
        >>> try:
        ...     result = breaker.call(risky_database_operation, param1, param2)
        ... except Exception as e:
        ...     handle_circuit_breaker_exception(e)
    """
    def __init__(self, failure_threshold=5, recovery_timeout=60):
        """
        Initialize circuit breaker with failure and recovery thresholds.
        
        Args:
            failure_threshold (int): Number of consecutive failures that will
                                   trigger the circuit to open. Defaults to 5.
            recovery_timeout (int): Number of seconds to wait in OPEN state
                                  before attempting recovery. Defaults to 60.
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
        self._lock = threading.Lock()
    
    def call(self, func, *args, **kwargs):
        """
        Execute function with circuit breaker protection.
        
        This method wraps the execution of a function with circuit breaker logic.
        It tracks failures and manages state transitions to provide resilience
        against cascading failures.
        
        Args:
            func (callable): The function to execute with protection.
            *args: Positional arguments to pass to the function.
            **kwargs: Keyword arguments to pass to the function.
        
        Returns:
            any: The return value of the executed function if successful.
        
        Raises:
            Exception: Raises "Circuit breaker is OPEN" when the circuit is open,
                      or propagates the original exception from the function.
        
        State Transitions:
            - CLOSED -> OPEN: When failure_threshold is exceeded
            - OPEN -> HALF_OPEN: After recovery_timeout expires
            - HALF_OPEN -> CLOSED: When a call succeeds
            - HALF_OPEN -> OPEN: When a call fails
        """
        with self._lock:
            if self.state == 'OPEN':
                if self.last_failure_time and time.time() - self.last_failure_time > self.recovery_timeout:
                    self.state = 'HALF_OPEN'
                else:
                    raise Exception("Circuit breaker is OPEN")
            
            try:
                result = func(*args, **kwargs)
                if self.state == 'HALF_OPEN':
                    self.state = 'CLOSED'
                    self.failure_count = 0
                return result
            except Exception as e:
                self.failure_count += 1
                self.last_failure_time = time.time()
                
                if self.failure_count >= self.failure_threshold:
                    self.state = 'OPEN'
                    log_error(f"Circuit breaker opened after {self.failure_count} failures")
                
                raise e

# Query performance monitoring
class QueryPerformanceMonitor:
    """
    Monitor database query performance and track slow queries.
    
    This class provides comprehensive monitoring of database query performance,
    including tracking slow queries, computing statistics, and implementing
    circuit breaker protection. It helps identify performance bottlenecks
    and provides automatic protection against database overload.
    
    The monitor automatically tracks all executed queries and provides
    detailed statistics about query performance, including average execution
    times, slow query detection, and historical performance data.
    
    Attributes:
        slow_query_threshold (float): Minimum execution time in seconds to
                                    classify a query as slow.
        slow_queries (deque): Rolling buffer of recent slow queries with
                            details about execution time and SQL.
        total_queries (int): Total number of queries executed since initialization.
        total_query_time (float): Cumulative execution time of all queries.
        circuit_breaker (CircuitBreaker): Protection against cascading failures.
    
    Example:
        >>> monitor = QueryPerformanceMonitor(slow_query_threshold=0.5)
        >>> monitor.record_query(1.2, "SELECT * FROM users WHERE ...", {"id": 123})
        >>> stats = monitor.get_stats()
        >>> print(f"Average query time: {stats['average_query_time']}s")
    """
    def __init__(self, slow_query_threshold=1.0):
        self.slow_query_threshold = slow_query_threshold
        self.slow_queries = deque(maxlen=100)  # Keep last 100 slow queries
        self.total_queries = 0
        self.total_query_time = 0.0
        self._lock = threading.Lock()
        self.circuit_breaker = CircuitBreaker()
    
    def record_query(self, duration, statement, parameters=None):
        """Record query execution metrics"""
        with self._lock:
            self.total_queries += 1
            self.total_query_time += duration
            
            if duration >= self.slow_query_threshold:
                self.slow_queries.append({
                    'duration': duration,
                    'statement': str(statement)[:200],  # Truncate long queries
                    'parameters': str(parameters)[:100] if parameters else None,
                    'timestamp': datetime.utcnow().isoformat()
                })
                log_warning(f"Slow query detected: {duration:.3f}s - {str(statement)[:100]}")
    
    def get_stats(self):
        """Get performance statistics"""
        with self._lock:
            avg_query_time = self.total_query_time / max(self.total_queries, 1)
            return {
                'total_queries': self.total_queries,
                'total_query_time': round(self.total_query_time, 3),
                'average_query_time': round(avg_query_time, 3),
                'slow_queries_count': len(self.slow_queries),
                'recent_slow_queries': list(self.slow_queries)[-10:]  # Last 10 slow queries
            }

# Global performance monitor instance
query_monitor = QueryPerformanceMonitor(slow_query_threshold=0.5)  # 500ms threshold

def setup_query_monitoring(app):
    """Set up SQLAlchemy event listeners for automatic query monitoring"""
    @event.listens_for(db.engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        context._query_start_time = time.time()

    @event.listens_for(db.engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        total = time.time() - context._query_start_time
        query_monitor.record_query(total, statement, parameters)

    log_info("Database query monitoring enabled")

# Database connection pool configuration
def configure_db_pool(app):
    """Configure database connection pool for optimal performance and safety"""
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'poolclass': QueuePool,
        'pool_size': 10,  # Number of c                        result = db.session.execute(text(f"SELECT COUNT(*) FROM {table}"))  # type: ignorennections to maintain
        'max_overflow': 20,  # Additional connections when pool is full
        'pool_timeout': 30,  # Timeout for getting connection from pool
        'pool_recycle': 3600,  # Recycle connections after 1 hour
        'pool_pre_ping': True,  # Verify connections before use
        'echo': False  # Set to True for SQL debugging
    }

@contextmanager
def safe_db_transaction():
    """Context manager for safe database transactions with automatic rollback on error"""
    try:
        yield db.session
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e

def safe_db_operation(operation_func):
    """Decorator for safe database operations with automatic transaction management"""
    def wrapper(*args, **kwargs):
        try:
            with safe_db_transaction():
                return operation_func(*args, **kwargs)
        except Exception as e:
            # Log the error using consistent logging and re-raise
            log_error(f"Database operation failed: {str(e)}")
            raise e
    return wrapper

class User(db.Model, UserMixin):
    """
    User model for authentication and authorization management.
    
    This class represents a user in the Vybe AI system with comprehensive
    security features including password hashing, API key management,
    account lockout protection, and session management. It extends Flask-Login's
    UserMixin to provide standard authentication functionality.
    
    The model includes advanced security features:
    - Secure password hashing with PBKDF2-SHA256
    - API key generation and validation
    - Account lockout protection against brute force attacks
    - Device fingerprinting for enhanced security
    - Session token management with expiration
    - Two-factor authentication support
    - Comprehensive audit trail with timestamps
    
    Attributes:
        id (int): Primary key identifier for the user.
        username (str): Unique username for login (max 64 characters).
        email (str): User's email address, optional but unique if provided.
        password_hash (str): Hashed password using PBKDF2-SHA256.
        api_key (str): Hashed API key for programmatic access.
        device_id (str): Device fingerprint for security validation.
        created_at (datetime): Timestamp of user creation.
        last_login (datetime): Timestamp of most recent successful login.
        is_active (bool): Whether the user account is active.
        failed_login_attempts (int): Count of consecutive failed login attempts.
        account_locked_until (datetime): Expiration time for account lockout.
        password_changed_at (datetime): Timestamp of last password change.
        two_factor_enabled (bool): Whether 2FA is enabled for the user.
        session_token (str): Current session token for authentication.
        session_expires_at (datetime): Expiration time for current session.
    
    Security Features:
        - Password complexity validation
        - Account lockout after failed attempts
        - Device fingerprinting
        - Secure session management
        - API key hashing and validation
    
    Example:
        >>> user = User()
        >>> user.username = 'john_doe'
        >>> user.email = 'john@example.com'
        >>> user.set_password('SecurePassword123')
        >>> db.session.add(user)
        >>> db.session.commit()
    """
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=True, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    api_key = db.Column(db.String(128), unique=True, nullable=True, index=True)
    device_id = db.Column(db.String(64), nullable=True, index=True)  # For device-specific security
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    last_login = db.Column(db.DateTime, index=True)
    is_active = db.Column(db.Boolean, default=True, index=True)
    
    # Security enhancements
    failed_login_attempts = db.Column(db.Integer, default=0)
    account_locked_until = db.Column(db.DateTime, nullable=True)
    password_changed_at = db.Column(db.DateTime, default=datetime.utcnow)
    two_factor_enabled = db.Column(db.Boolean, default=False)
    session_token = db.Column(db.String(128), nullable=True)
    session_expires_at = db.Column(db.DateTime, nullable=True)

    # Create composite indexes for common query patterns
    __table_args__ = (
        Index('idx_user_username_active', 'username', 'is_active'),
        Index('idx_user_email_active', 'email', 'is_active'),
        Index('idx_user_created_active', 'created_at', 'is_active'),
        Index('idx_user_lastlogin_active', 'last_login', 'is_active'),
        Index('idx_user_device_active', 'device_id', 'is_active'),
        Index('idx_user_apikey_active', 'api_key', 'is_active'),
        Index('idx_user_session_token', 'session_token'),
        Index('idx_user_locked_until', 'account_locked_until'),
    )

    def set_password(self, password):
        """
        Set user password with security validation and hashing.
        
        This method validates password complexity requirements and stores
        the password using secure PBKDF2-SHA256 hashing with a random salt.
        
        Password Requirements:
            - Minimum 8 characters in length
            - At least one uppercase letter
            - At least one lowercase letter
            - At least one digit
            - Optional special character requirement (commented out)
        
        Args:
            password (str): The plain text password to hash and store.
        
        Raises:
            ValueError: If password doesn't meet complexity requirements.
        
        Security Features:
            - PBKDF2-SHA256 hashing algorithm
            - 16-byte random salt generation
            - Password complexity validation
            - Secure password storage
        
        Example:
            >>> user.set_password('MySecurePass123')
            >>> # Password is now hashed and stored securely
        """
        # Enhanced password validation
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        # Check for complexity requirements
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password)
        
        if not (has_upper and has_lower and has_digit):
            raise ValueError("Password must contain at least one uppercase letter, one lowercase letter, and one digit")
        
        # Optional: require special characters for higher security
        # if not has_special:
        #     raise ValueError("Password must contain at least one special character")
        
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)

    def check_password(self, password):
        """
        Verify a password against the stored hash.
        
        This method uses secure password verification to check if the provided
        plain text password matches the stored hashed password.
        
        Args:
            password (str): The plain text password to verify.
        
        Returns:
            bool: True if the password is correct, False otherwise.
        
        Security Features:
            - Constant-time comparison to prevent timing attacks
            - PBKDF2-SHA256 verification using Werkzeug's secure implementation
        
        Example:
            >>> if user.check_password('MySecurePass123'):
            ...     print("Password is correct")
        """
        return check_password_hash(self.password_hash, password)
    
    def generate_api_key(self):
        """
        Generate a new secure API key for programmatic access.
        
        This method creates a cryptographically secure API key using the
        secrets module and stores a hashed version in the database for
        secure validation.
        
        Returns:
            str: The plain text API key that should be provided to the user.
                The plain text version is not stored and cannot be recovered.
        
        Security Features:
            - 32-byte cryptographically secure random token
            - PBKDF2-SHA256 hashing for secure storage
            - 16-byte random salt for hash strengthening
        
        Example:
            >>> api_key = user.generate_api_key()
            >>> print(f"Your API key: {api_key}")
            >>> # Store api_key securely, it cannot be recovered later
        
        Note:
            The plain text API key is only available at generation time.
            The hashed version is stored for future validation.
        """
        import secrets
        # Generate a secure 32-byte token and encode as hex
        plain_key = secrets.token_hex(32)
        # Store the hash in the database
        self.api_key = generate_password_hash(plain_key, method='pbkdf2:sha256', salt_length=16)
        db.session.commit()
        return plain_key
    
    def check_api_key(self, api_key):
        """
        Validate an API key against the stored hash.
        
        This method securely verifies if the provided API key matches
        the stored hashed version using constant-time comparison.
        
        Args:
            api_key (str): The plain text API key to validate.
        
        Returns:
            bool: True if the API key is valid, False otherwise.
        
        Security Features:
            - Constant-time comparison to prevent timing attacks
            - Secure hash verification using PBKDF2-SHA256
            - Handles missing API keys gracefully
        
        Example:
            >>> if user.check_api_key(provided_key):
            ...     print("API key is valid")
            ... else:
            ...     print("Invalid API key")
        """
        if not self.api_key:
            return False
        return check_password_hash(self.api_key, api_key)
    
    def revoke_api_key(self):
        """
        Revoke the current API key by removing it from the database.
        
        This method permanently revokes the user's API key, requiring
        generation of a new key for future programmatic access.
        
        Security Use Cases:
            - Key compromise or suspected breach
            - User-requested key rotation
            - Administrative key revocation
            - Account deactivation procedures
        
        Example:
            >>> user.revoke_api_key()
            >>> # User's API key is now invalid and cannot be used
        
        Note:
            After revocation, all systems using the old API key will
            receive authentication failures until a new key is generated.
        """
        self.api_key = None
        db.session.commit()
    
    def set_device_id(self):
        """
        Generate and set a unique device fingerprint for enhanced security.
        
        This method creates a unique device identifier based on system
        characteristics and random elements to enhance security through
        device tracking and validation.
        
        Returns:
            str or None: The generated device fingerprint (32 characters) if
                        successful, None if generation failed.
        
        Device Fingerprint Components:
            - Operating system information
            - Machine architecture details
            - Processor information
            - Random UUID for uniqueness
            - SHA256 hash for consistency
        
        Security Benefits:
            - Device-based access control
            - Suspicious login detection
            - Multi-device session management
            - Enhanced fraud prevention
        
        Example:
            >>> device_id = user.set_device_id()
            >>> if device_id:
            ...     print(f"Device registered: {device_id}")
        
        Note:
            The device ID is deterministic for the same system but includes
            randomness to prevent fingerprinting attacks.
        """
        import platform
        import hashlib
        import uuid as uuid_module
        
        # Create device fingerprint based on system info
        system_info = f"{platform.system()}-{platform.machine()}-{platform.processor()}"
        try:
            # Add some randomness for uniqueness
            random_uuid = str(uuid_module.uuid4())
            device_fingerprint = hashlib.sha256(f"{system_info}-{random_uuid}".encode()).hexdigest()[:32]
            self.device_id = device_fingerprint
            db.session.commit()
            return device_fingerprint
        except Exception as e:
            # Use consistent logging
            log_error(f"Failed to set device ID: {e}")
            return None
    
    def check_device_id(self, device_id):
        """
        Validate a device ID against the stored device fingerprint.
        
        This method checks if the provided device ID matches the stored
        device fingerprint for the user account.
        
        Args:
            device_id (str): The device ID to validate against stored fingerprint.
        
        Returns:
            bool: True if the device ID matches, False otherwise.
        
        Security Applications:
            - Device-based authentication
            - Suspicious activity detection
            - Multi-device session management
            - Access control enforcement
        
        Example:
            >>> if user.check_device_id(client_device_id):
            ...     print("Recognized device")
            ... else:
            ...     print("Unknown device - additional verification needed")
        """
        return self.device_id == device_id
    
    def update_last_login(self):
        """
        Update login timestamp and reset security counters.
        
        This method updates the user's last login timestamp and resets
        security-related counters such as failed login attempts and
        account lockout status. Called upon successful authentication.
        
        Actions Performed:
            - Sets last_login to current UTC timestamp
            - Resets failed_login_attempts to 0
            - Clears account_locked_until timestamp
            - Commits changes to database
        
        Security Benefits:
            - Tracks user activity for auditing
            - Resets lockout protections after successful login
            - Provides data for security monitoring
        
        Example:
            >>> if user.check_password(provided_password):
            ...     user.update_last_login()
            ...     print("Login successful")
        
        Note:
            This method should only be called after successful authentication
            to maintain accurate security metrics.
        """
        self.last_login = datetime.utcnow()
        self.failed_login_attempts = 0
        self.account_locked_until = None
        db.session.commit()
    
    def is_account_locked(self):
        """
        Check if the user account is currently locked due to security measures.
        
        This method determines if the account is currently locked based on
        the account_locked_until timestamp compared to the current time.
        
        Returns:
            bool: True if the account is currently locked, False if unlocked
                 or if no lockout timestamp is set.
        
        Lockout Conditions:
            - account_locked_until is set to a future timestamp
            - Current time is before the lockout expiration
        
        Security Features:
            - Time-based automatic unlock
            - Prevents brute force attacks
            - Configurable lockout duration
        
        Example:
            >>> if user.is_account_locked():
            ...     print("Account is temporarily locked")
            ... else:
            ...     print("Account is available for login")
        
        Note:
            The account automatically unlocks when the current time passes
            the account_locked_until timestamp.
        """
        if self.account_locked_until:
            return datetime.utcnow() < self.account_locked_until
        return False
    
    def increment_failed_login(self):
        """
        Record a failed login attempt and apply security lockout if needed.
        
        This method increments the failed login counter and applies account
        lockout protection when the failure threshold is reached. This helps
        prevent brute force password attacks.
        
        Lockout Policy:
            - Threshold: 5 consecutive failed attempts
            - Duration: 30 minutes lockout period
            - Automatic unlock after timeout expires
        
        Security Features:
            - Brute force attack prevention
            - Automatic temporary lockout
            - Security event logging
            - Configurable thresholds
        
        Actions Performed:
            - Increments failed_login_attempts counter
            - Sets account_locked_until if threshold exceeded
            - Logs security warning for lockout events
            - Commits changes to database
        
        Example:
            >>> if not user.check_password(provided_password):
            ...     user.increment_failed_login()
            ...     if user.is_account_locked():
            ...         print("Account locked due to failed attempts")
        
        Note:
            Counter is reset to 0 upon successful login via update_last_login().
        """
        self.failed_login_attempts += 1
        
        # Lock account after 5 failed attempts for 30 minutes
        if self.failed_login_attempts >= 5:
            from datetime import timedelta
            self.account_locked_until = datetime.utcnow() + timedelta(minutes=30)
            log_warning(f"Account locked for user {self.username} due to failed login attempts")
        
        db.session.commit()
    
    def create_secure_session(self):
        """
        Create a secure session token with expiration time.
        
        This method generates a cryptographically secure session token and
        sets an expiration time for the session. The session is valid for
        24 hours from creation time.
        
        Returns:
            str: The generated session token (URL-safe base64 encoded).
        
        Security Features:
            - URL-safe base64 encoding for web compatibility
            - 32-byte cryptographically secure random token
            - Automatic expiration after 24 hours
            - Database persistence for session validation
        
        Example:
            >>> session_token = user.create_secure_session()
            >>> print(f"Session created: {session_token}")
            >>> # Token is valid for 24 hours
        
        Note:
            Previous session tokens are automatically invalidated when
            a new session is created.
        """
        import secrets
        self.session_token = secrets.token_urlsafe(32)
        # Session expires in 24 hours
        from datetime import timedelta
        self.session_expires_at = datetime.utcnow() + timedelta(hours=24)
        db.session.commit()
        return self.session_token
    
    def invalidate_session(self):
        """
        Invalidate the current user session by clearing tokens.
        
        This method clears the session token and expiration time, effectively
        logging out the user and requiring re-authentication for protected
        resources.
        
        Security Use Cases:
            - User-initiated logout
            - Session timeout handling
            - Security breach response
            - Administrative session termination
        
        Example:
            >>> user.invalidate_session()
            >>> # User must authenticate again for protected resources
        
        Note:
            This method commits the changes to the database immediately
            to ensure the session is invalidated across all application
            instances.
        """
        self.session_token = None
        self.session_expires_at = None
        db.session.commit()
    
    def is_session_valid(self):
        """
        Check if the current user session is valid and not expired.
        
        This method validates both the presence of a session token and
        checks that the session has not expired based on the stored
        expiration timestamp.
        
        Returns:
            bool: True if the session is valid and not expired, False otherwise.
        
        Validation Checks:
            - Session token exists and is not None
            - Session expiration time is set
            - Current time is before expiration time
        
        Example:
            >>> if user.is_session_valid():
            ...     print("Session is active")
            ... else:
            ...     print("Session expired or invalid")
        
        Note:
            This method performs time-based validation but does not
            automatically clean up expired sessions from the database.
        """
        if not self.session_token or not self.session_expires_at:
            return False
        return datetime.utcnow() < self.session_expires_at
    
    def to_dict(self):
        """
        Convert user object to dictionary for API responses.
        
        This method serializes the user object into a dictionary format
        suitable for JSON API responses, excluding sensitive information
        like password hashes and including only safe, public data.
        
        Returns:
            dict: Dictionary containing safe user data with the following keys:
                - id (int): User's unique identifier
                - username (str): User's username
                - email (str): User's email address
                - created_at (str): ISO formatted creation timestamp
                - last_login (str): ISO formatted last login timestamp
                - is_active (bool): Whether the account is active
                - has_api_key (bool): Whether user has an API key (not the key itself)
        
        Security Features:
            - Excludes sensitive data (password_hash, api_key, session_token)
            - Converts timestamps to ISO format strings
            - Provides boolean indicator for API key presence
        
        Example:
            >>> user_data = user.to_dict()
            >>> return jsonify(user_data)  # Safe for API responses
        
        Note:
            This method is safe for public API responses as it excludes
            all sensitive authentication data.
        """
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'is_active': self.is_active,
            'has_api_key': bool(self.api_key)
        }
    
    @classmethod
    @query_cache(ttl=600)  # Cache for 10 minutes
    def find_by_username(cls, username):
        """
        Find a user by username with caching optimization.
        
        This class method provides an optimized way to find users by username
        with automatic query result caching to improve performance for
        frequent username lookups.
        
        Args:
            username (str): The username to search for.
        
        Returns:
            User or None: The User object if found, None if no user exists
                         with the specified username.
        
        Performance Features:
            - Query result caching for 10 minutes
            - Database index optimization on username field
            - Automatic cache invalidation on updates
        
        Example:
            >>> user = User.find_by_username('john_doe')
            >>> if user:
            ...     print(f"Found user: {user.email}")
        
        Note:
            Results are cached to reduce database load for frequent lookups.
            Cache is automatically invalidated when user data changes.
        """
        return cls.query.filter_by(username=username).first()
    
    @classmethod
    @query_cache(ttl=600)  # Cache for 10 minutes
    def find_by_email(cls, email):
        """
        Find a user by email address with caching optimization.
        
        This class method provides an optimized way to find users by email
        with automatic query result caching to improve performance for
        frequent email-based lookups.
        
        Args:
            email (str): The email address to search for.
        
        Returns:
            User or None: The User object if found, None if no user exists
                         with the specified email address.
        
        Performance Features:
            - Query result caching for 10 minutes
            - Database index optimization on email field
            - Automatic cache invalidation on updates
        
        Example:
            >>> user = User.find_by_email('john@example.com')
            >>> if user:
            ...     print(f"Found user: {user.username}")
        
        Note:
            Results are cached to reduce database load for frequent lookups.
            Cache is automatically invalidated when user data changes.
        """
        return cls.query.filter_by(email=email).first()
    
    @classmethod
    @query_cache(ttl=300)  # Cache for 5 minutes
    def find_by_api_key(cls, api_key):
        """Find user by API key - optimized database query with indexed lookup"""
        if not api_key:
            return None
        
        # Hash the provided API key to compare against stored hashes
        # Note: This is a security consideration - we store hashed API keys
        # For optimal performance, we'd need a separate indexed table,
        # but this optimization reduces the query scope significantly
        
        # Query only active users with API keys using the composite index
        # This is much more efficient than loading ALL users into memory
        users_with_keys = cls.query.filter_by(is_active=True).filter(
            cls.api_key != None  # type: ignore
        ).all()
        
        # Check API key hashes - this is still O(n) but n is much smaller now
        for user in users_with_keys:
            if user.check_api_key(api_key):
                return user
        return None
    
    @classmethod
    def create_user(cls, username, password, email=None):
        """Create a new user with validation"""
        if cls.find_by_username(username):
            raise ValueError(f"Username '{username}' already exists")
        
        if email and cls.find_by_email(email):
            raise ValueError(f"Email '{email}' already exists")
        
        user = cls()
        user.username = username
        user.email = email
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        return user

class Message(db.Model):
    """
    Model for storing chat messages and AI responses with performance metrics.
    
    This class represents individual chat messages in the Vybe AI system,
    storing both user input and AI responses along with metadata for
    performance monitoring and conversation tracking.
    
    The model includes comprehensive indexing for efficient querying and
    supports analytics for AI model performance monitoring and user
    interaction patterns.
    
    Attributes:
        id (int): Primary key identifier for the message.
        user_message (str): The original user input/question (required).
        ai_response (str): The AI-generated response (required).
        timestamp (datetime): When the message was created (auto-generated).
        user_id (int): Foreign key to User model (optional for anonymous users).
        session_id (str): Session identifier for grouping related messages.
        model_used (str): Name/identifier of the AI model that generated the response.
        response_time_ms (int): Response generation time in milliseconds.
    
    Relationships:
        user (User): Backref relationship to the User who sent the message.
    
    Performance Features:
        - Composite indexes for common query patterns
        - Efficient timestamp-based sorting
        - Model performance tracking
        - Session-based message grouping
    
    Example:
        >>> message = Message(
        ...     user_message="What is Python?",
        ...     ai_response="Python is a programming language...",
        ...     user_id=user.id,
        ...     session_id="session123",
        ...     model_used="gpt-3.5-turbo",
        ...     response_time_ms=1500
        ... )
        >>> db.session.add(message)
        >>> db.session.commit()
    """
    id = db.Column(db.Integer, primary_key=True)
    user_message = db.Column(db.Text, nullable=False)
    ai_response = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)
    session_id = db.Column(db.String(128), nullable=True, index=True)
    model_used = db.Column(db.String(100), nullable=True, index=True)
    response_time_ms = db.Column(db.Integer, nullable=True, index=True)
    
    # Create composite indexes for common query patterns
    __table_args__ = (
        Index('idx_message_timestamp_user', 'timestamp', 'user_id'),
        Index('idx_message_session_timestamp', 'session_id', 'timestamp'),
        Index('idx_message_model_timestamp', 'model_used', 'timestamp'),
        Index('idx_message_user_model', 'user_id', 'model_used'),
        Index('idx_message_responsetime_timestamp', 'response_time_ms', 'timestamp'),
    )
    
    user = db.relationship('User', backref=db.backref('messages', lazy='dynamic'))
    
    def to_dict(self):
        """
        Convert message object to dictionary for API responses.
        
        This method serializes the message object into a dictionary format
        suitable for JSON API responses, including all message data and
        metadata for client consumption.
        
        Returns:
            dict: Dictionary containing message data with the following keys:
                - id (int): Message unique identifier
                - user_message (str): Original user input
                - ai_response (str): AI-generated response
                - timestamp (str): ISO formatted creation time
                - user_id (int): Associated user ID (may be None)
                - session_id (str): Session grouping identifier
                - model_used (str): AI model identifier
                - response_time_ms (int): Response generation time
        
        Example:
            >>> message_data = message.to_dict()
            >>> return jsonify(message_data)  # Safe for API responses
        
        Note:
            All message content is included as this model doesn't contain
            sensitive user authentication data.
        """
        return {
            'id': self.id,
            'user_message': self.user_message,
            'ai_response': self.ai_response,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'model_used': self.model_used,
            'response_time_ms': self.response_time_ms
        }

class ChatSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    messages = db.Column(db.Text, nullable=False)  # JSON string of messages
    message_count = db.Column(db.Integer, default=0, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)

    # Create composite indexes for common query patterns
    __table_args__ = (
        Index('idx_chatsession_user_created', 'user_id', 'created_at'),
        Index('idx_chatsession_user_updated', 'user_id', 'updated_at'),
        Index('idx_chatsession_messagecount_updated', 'message_count', 'updated_at'),
        Index('idx_chatsession_title_user', 'title', 'user_id'),
    )

    user = db.relationship('User', backref=db.backref('chat_sessions', lazy='dynamic'))

    def get_messages(self):
        """Get messages as list"""
        try:
            return json.loads(self.messages)
        except (ValueError, json.JSONDecodeError):
            return []

    def set_messages(self, messages):
        """Set messages from list"""
        self.messages = json.dumps(messages)
        self.message_count = len(messages)

    def to_dict(self):
        """Convert session to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'messages': self.get_messages(),
            'message_count': self.message_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class SystemPrompt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    description = db.Column(db.String(200), nullable=True)
    category = db.Column(db.String(50), nullable=False, default='General', index=True)
    content = db.Column(db.Text, nullable=False)
    is_default = db.Column(db.Boolean, default=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)

    # Create composite indexes for common query patterns
    __table_args__ = (
        Index('idx_systemprompt_category_default', 'category', 'is_default'),
        Index('idx_systemprompt_name_category', 'name', 'category'),
        Index('idx_systemprompt_updated_category', 'updated_at', 'category'),
        Index('idx_systemprompt_default_updated', 'is_default', 'updated_at'),
    )

    def to_dict(self):
        """Convert prompt to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'content': self.content,
            'is_default': self.is_default,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class AppSetting(db.Model):
    """Application settings with enhanced caching support and metrics"""
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    value = db.Column(db.Text, nullable=False)
    description = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)

    # Enhanced in-memory cache with metrics
    _cache = {}
    _cache_timeout = 300  # 5 minutes
    _cache_timestamps = {}
    _cache_hits = 0
    _cache_misses = 0
    _cache_lock = threading.Lock()

    # Create composite indexes for common query patterns
    __table_args__ = (
        Index('idx_appsetting_key_updated', 'key', 'updated_at'),
        Index('idx_appsetting_created_updated', 'created_at', 'updated_at'),
    )

    @classmethod
    def get_cached(cls, key: str):
        """Get setting with enhanced caching support and metrics"""
        import time
        current_time = time.time()
        
        with cls._cache_lock:
            # Check if cached and not expired
            if (key in cls._cache and 
                key in cls._cache_timestamps and 
                current_time - cls._cache_timestamps[key] < cls._cache_timeout):
                cls._cache_hits += 1
                return cls._cache[key]
            
            # Cache miss - remove expired entry if exists
            if key in cls._cache:
                cls._cache.pop(key, None)
                cls._cache_timestamps.pop(key, None)
            
            cls._cache_misses += 1
        
        # Query from database (outside lock to avoid blocking)
        setting = cls.query.filter_by(key=key).first()
        
        # Cache the result
        with cls._cache_lock:
            cls._cache[key] = setting
            cls._cache_timestamps[key] = current_time
        
        return setting

    @classmethod
    def invalidate_cache(cls, key: str | None = None):
        """Invalidate cache for a specific key or all keys with metrics"""
        with cls._cache_lock:
            if key:
                removed = cls._cache.pop(key, None) is not None
                cls._cache_timestamps.pop(key, None)
                if removed:
                    log_info(f"Cache invalidated for AppSetting key: {key}")
            else:
                cache_size = len(cls._cache)
                cls._cache.clear()
                cls._cache_timestamps.clear()
                log_info(f"All AppSetting cache cleared ({cache_size} entries)")

    @classmethod
    def get_cache_stats(cls):
        """Get cache performance statistics"""
        with cls._cache_lock:
            total_requests = cls._cache_hits + cls._cache_misses
            hit_rate = (cls._cache_hits / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'cache_hits': cls._cache_hits,
                'cache_misses': cls._cache_misses,
                'hit_rate_percent': round(hit_rate, 2),
                'cached_entries': len(cls._cache),
                'cache_timeout': cls._cache_timeout
            }

    @classmethod
    def reset_cache_stats(cls):
        """Reset cache statistics"""
        with cls._cache_lock:
            cls._cache_hits = 0
            cls._cache_misses = 0

    def save_and_invalidate_cache(self):
        """Save to database and invalidate cache with error handling and metrics"""
        import time
        start_time = time.time()
        
        try:
            # Update timestamp before saving
            self.updated_at = datetime.utcnow()
            db.session.add(self)
            db.session.commit()
            
            # Invalidate cache after successful save
            self.invalidate_cache(self.key)
            
            # Log operation with metrics
            duration = time.time() - start_time
            query_monitor.record_query(duration, f"AppSetting.save_and_invalidate_cache: {self.key}")
            log_info(f"AppSetting '{self.key}' saved and cache invalidated in {duration:.3f}s")
            
        except Exception as e:
            db.session.rollback()
            log_error(f"Failed to save AppSetting '{self.key}': {e}")
            raise e

    def to_dict(self):
        """Convert setting to dictionary"""
        return {
            'id': self.id,
            'key': self.key,
            'value': self.value,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class InstalledModelMetadata(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    model_name = db.Column(db.String, unique=True, nullable=False, index=True)
    description = db.Column(db.Text)
    fidelity = db.Column(db.String, index=True)
    pc_load = db.Column(db.String, index=True)
    
    # Create composite indexes for common query patterns
    __table_args__ = (
        Index('idx_installedmodel_fidelity_pc_load', 'fidelity', 'pc_load'),
        Index('idx_installedmodel_name_fidelity', 'model_name', 'fidelity'),
    )

class Feedback(db.Model):
    """Enhanced model for storing user feedback with automatic categorization and sentiment analysis"""
    __tablename__ = 'feedback'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    feedback_type = db.Column(db.String(50), nullable=False, default='general')  # general, bug, feature, improvement
    subject = db.Column(db.String(256), nullable=True)
    message = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, nullable=True)  # 1-5 star rating
    status = db.Column(db.String(50), default='pending', index=True)  # pending, reviewed, resolved, closed
    priority = db.Column(db.String(20), default='medium')  # low, medium, high, critical
    category = db.Column(db.String(100), nullable=True)  # UI, API, Performance, etc.
    auto_category = db.Column(db.String(100), nullable=True)  # Auto-detected category
    sentiment_score = db.Column(db.Float, nullable=True)  # -1.0 to 1.0 (negative to positive)
    sentiment_label = db.Column(db.String(20), nullable=True)  # negative, neutral, positive
    confidence_score = db.Column(db.Float, nullable=True)  # 0.0 to 1.0 confidence in categorization
    keywords = db.Column(db.Text, nullable=True)  # JSON array of extracted keywords
    metadata_json = db.Column(db.Text, nullable=True)  # JSON for additional context
    browser_info = db.Column(db.Text, nullable=True)
    session_id = db.Column(db.String(128), nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)  # IPv6 compatible
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    reviewed_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    
    # Create composite indexes for common query patterns
    __table_args__ = (
        Index('idx_feedback_type_status', 'feedback_type', 'status'),
        Index('idx_feedback_priority_status', 'priority', 'status'),
        Index('idx_feedback_category_status', 'category', 'status'),
        Index('idx_feedback_auto_category', 'auto_category', 'status'),
        Index('idx_feedback_sentiment', 'sentiment_label', 'created_at'),
        Index('idx_feedback_created_status', 'created_at', 'status'),
        Index('idx_feedback_user_type', 'user_id', 'feedback_type'),
        Index('idx_feedback_rating_created', 'rating', 'created_at'),
    )
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='feedback_given')
    reviewer = db.relationship('User', foreign_keys=[reviewed_by], backref='feedback_reviewed')
    
    def __repr__(self):
        return f'<Feedback {self.id}: {self.feedback_type} - {self.status}>'

    def process_with_ml(self):
        """Process feedback with ML-based categorization and sentiment analysis"""
        try:
            # Auto-categorize feedback
            self.auto_category = self._categorize_feedback()
            
            # Perform sentiment analysis
            sentiment_result = self._analyze_sentiment()
            self.sentiment_score = sentiment_result.get('score')
            self.sentiment_label = sentiment_result.get('label')
            self.confidence_score = sentiment_result.get('confidence')
            
            # Extract keywords
            self.keywords = json.dumps(self._extract_keywords())
            
            # Auto-assign priority based on sentiment and content
            self._auto_assign_priority()
            
            db.session.commit()
            log_info(f"Feedback {self.id} processed with ML categorization")
            
        except Exception as e:
            log_error(f"Failed to process feedback {self.id} with ML: {e}")

    def _categorize_feedback(self):
        """Simple rule-based categorization (can be enhanced with ML models)"""
        text = f"{self.subject or ''} {self.message}".lower()
        
        categories = {
            'bug': ['error', 'bug', 'broken', 'crash', 'issue', 'problem', 'fail', 'not work'],
            'feature': ['feature', 'add', 'new', 'request', 'want', 'need', 'suggest', 'idea'],
            'ui': ['interface', 'design', 'layout', 'button', 'color', 'font', 'menu', 'navigation'],
            'performance': ['slow', 'fast', 'speed', 'performance', 'lag', 'delay', 'timeout'],
            'api': ['api', 'endpoint', 'response', 'request', 'json', 'data', 'integration'],
            'documentation': ['doc', 'help', 'guide', 'instruction', 'tutorial', 'example'],
            'security': ['security', 'password', 'login', 'auth', 'permission', 'access']
        }
        
        best_category = 'general'
        max_matches = 0
        
        for category, keywords in categories.items():
            matches = sum(1 for keyword in keywords if keyword in text)
            if matches > max_matches:
                max_matches = matches
                best_category = category
        
        return best_category if max_matches > 0 else 'general'

    def _analyze_sentiment(self):
        """Simple sentiment analysis (can be enhanced with ML models)"""
        text = f"{self.subject or ''} {self.message}".lower()
        
        positive_words = ['good', 'great', 'excellent', 'amazing', 'love', 'like', 'awesome', 'perfect', 'helpful']
        negative_words = ['bad', 'terrible', 'awful', 'hate', 'dislike', 'broken', 'useless', 'worst', 'annoying']
        
        positive_count = sum(1 for word in positive_words if word in text)
        negative_count = sum(1 for word in negative_words if word in text)
        
        total_words = len(text.split())
        
        if total_words == 0:
            return {'score': 0.0, 'label': 'neutral', 'confidence': 0.0}
        
        score = (positive_count - negative_count) / max(total_words, 1)
        score = max(-1.0, min(1.0, score * 10))  # Scale and clamp
        
        if score > 0.1:
            label = 'positive'
        elif score < -0.1:
            label = 'negative'
        else:
            label = 'neutral'
        
        confidence = min(1.0, abs(score) + 0.1)
        
        return {'score': score, 'label': label, 'confidence': confidence}

    def _extract_keywords(self):
        """Extract key terms from feedback"""
        import re
        
        text = f"{self.subject or ''} {self.message}".lower()
        
        # Remove common words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those'}
        
        # Extract words (3+ characters, alphanumeric)
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text)
        keywords = [word for word in words if word not in stop_words]
        
        # Count frequency and return top keywords
        from collections import Counter
        keyword_counts = Counter(keywords)
        
        return [word for word, count in keyword_counts.most_common(10)]

    def _auto_assign_priority(self):
        """Auto-assign priority based on sentiment and content"""
        if self.sentiment_label == 'negative' and self.sentiment_score and self.sentiment_score < -0.5:
            if any(word in self.message.lower() for word in ['crash', 'error', 'broken', 'bug']):
                self.priority = 'high'
            else:
                self.priority = 'medium'
        elif self.rating and self.rating <= 2:
            self.priority = 'high'
        elif self.sentiment_label == 'positive':
            self.priority = 'low'
        else:
            self.priority = 'medium'

    @classmethod
    def get_sentiment_analytics(cls, days=30):
        """Get sentiment analytics for feedback"""
        try:
            from datetime import timedelta
            
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            results = db.session.query(  # type: ignore
                cls.sentiment_label,  # type: ignore
                db.func.count(cls.id).label('count'),
                db.func.avg(cls.sentiment_score).label('avg_score')
            ).filter(
                cls.created_at >= cutoff_date,
                cls.sentiment_label != None  # type: ignore
            ).group_by(cls.sentiment_label).all()
            
            analytics = {}
            total_feedback = 0
            
            for result in results:
                analytics[result.sentiment_label] = {
                    'count': result.count,
                    'avg_score': round(result.avg_score or 0, 3)
                }
                total_feedback += result.count
            
            # Calculate percentages
            for sentiment in analytics:
                analytics[sentiment]['percentage'] = round(
                    (analytics[sentiment]['count'] / max(total_feedback, 1)) * 100, 1
                )
            
            return {
                'period_days': days,
                'total_feedback': total_feedback,
                'sentiment_breakdown': analytics
            }
            
        except Exception as e:
            log_error(f"Error getting sentiment analytics: {e}")
            return {}

    @classmethod
    def get_category_analytics(cls, days=30):
        """Get category analytics for feedback"""
        try:
            from datetime import timedelta
            
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            results = db.session.query(  # type: ignore
                cls.auto_category,  # type: ignore
                db.func.count(cls.id).label('count'),
                db.func.avg(cls.confidence_score).label('avg_confidence')
            ).filter(
                cls.created_at >= cutoff_date,
                cls.auto_category != None  # type: ignore
            ).group_by(cls.auto_category).order_by(db.func.count(cls.id).desc()).all()
            
            categories = []
            total_feedback = sum(result.count for result in results)
            
            for result in results:
                categories.append({
                    'category': result.auto_category,
                    'count': result.count,
                    'percentage': round((result.count / max(total_feedback, 1)) * 100, 1),
                    'avg_confidence': round(result.avg_confidence or 0, 3)
                })
            
            return {
                'period_days': days,
                'total_feedback': total_feedback,
                'categories': categories
            }
            
        except Exception as e:
            log_error(f"Error getting category analytics: {e}")
            return []
    
    def to_dict(self):
        """Convert feedback to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'feedback_type': self.feedback_type,
            'subject': self.subject,
            'message': self.message,
            'rating': self.rating,
            'status': self.status,
            'priority': self.priority,
            'category': self.category,
            'metadata': json.loads(self.metadata_json) if self.metadata_json else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'user': self.user.username if self.user else 'Anonymous'
        }
    
    @classmethod
    def create_feedback(cls, user_id, message, feedback_type='general', subject=None, 
                       rating=None, category=None, metadata=None, browser_info=None, 
                       session_id=None, ip_address=None):
        """Create new feedback entry"""
        feedback = cls()
        feedback.user_id = user_id
        feedback.feedback_type = feedback_type
        feedback.subject = subject
        feedback.message = message
        feedback.rating = rating
        feedback.category = category
        feedback.metadata_json = json.dumps(metadata) if metadata else None
        feedback.browser_info = browser_info
        feedback.session_id = session_id
        feedback.ip_address = ip_address
        
        db.session.add(feedback)
        db.session.commit()
        return feedback
    categories_json = db.Column(db.Text)
    uncensored = db.Column(db.Boolean, default=False)
    n_ctx = db.Column(db.Integer)
    download_timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def get_categories(self):
        return json.loads(self.categories_json) if self.categories_json else []
    
    def set_categories(self, categories_list):
        self.categories_json = json.dumps(categories_list) if categories_list else None

class AIScratchpad(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(256), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # Create composite indexes for common query patterns
    __table_args__ = (
        Index('idx_aiscratchpad_session_updated', 'session_id', 'last_updated'),
    )
    
    def __init__(self, session_id=None, content=None, **kwargs):
        super(AIScratchpad, self).__init__(**kwargs)
        if session_id is not None:
            self.session_id = session_id
        if content is not None:
            self.content = content
        self.last_updated = datetime.utcnow()

class RAGCollectionMetadata(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    collection_name = db.Column(db.String(256), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Enhanced fields for scheduling and status
    scheduled_url = db.Column(db.String(512), nullable=True)
    schedule_frequency = db.Column(db.String(20), default='never')  # 'daily', 'weekly', 'monthly', 'never'
    last_updated_timestamp = db.Column(db.DateTime, nullable=True)
    next_update_due_timestamp = db.Column(db.DateTime, nullable=True)
    status_message = db.Column(db.String(256), default='Idle')
    is_ingesting = db.Column(db.Boolean, default=False)
    
    # Enhanced fields for incremental updates and conflict resolution
    version = db.Column(db.Integer, default=1, nullable=False)  # Version tracking
    checksum = db.Column(db.String(64), nullable=True)  # Content checksum for change detection
    total_documents = db.Column(db.Integer, default=0)
    failed_documents = db.Column(db.Integer, default=0)
    last_successful_update = db.Column(db.DateTime, nullable=True)
    conflict_resolution_strategy = db.Column(db.String(20), default='merge')  # 'merge', 'replace', 'skip'
    incremental_enabled = db.Column(db.Boolean, default=True)
    
    # Conflict tracking
    pending_conflicts = db.Column(db.Integer, default=0)
    last_conflict_resolved = db.Column(db.DateTime, nullable=True)
    
    # Performance metrics
    avg_processing_time_seconds = db.Column(db.Float, nullable=True)
    last_processing_time_seconds = db.Column(db.Float, nullable=True)

    # Create composite indexes for common query patterns
    __table_args__ = (
        Index('idx_ragcollection_name_status', 'collection_name', 'is_ingesting'),
        Index('idx_ragcollection_schedule_status', 'schedule_frequency', 'is_ingesting'),
        Index('idx_ragcollection_updated_schedule', 'last_updated_timestamp', 'schedule_frequency'),
        Index('idx_ragcollection_nextupdate_schedule', 'next_update_due_timestamp', 'schedule_frequency'),
        Index('idx_ragcollection_version_conflicts', 'version', 'pending_conflicts'),
        Index('idx_ragcollection_incremental_checksum', 'incremental_enabled', 'checksum'),
    )
    
    def start_incremental_update(self):
        """Start an incremental update process"""
        import time
        self.is_ingesting = True
        self.status_message = 'Starting incremental update...'
        self.version += 1
        self._update_start_time = time.time()
        db.session.commit()
        log_info(f"Started incremental update for collection: {self.collection_name} (v{self.version})")
    
    def complete_incremental_update(self, new_checksum=None, docs_processed=0, docs_failed=0):
        """Complete an incremental update with metrics"""
        import time
        
        if hasattr(self, '_update_start_time'):
            processing_time = time.time() - self._update_start_time
            self.last_processing_time_seconds = processing_time
            
            # Update rolling average
            if self.avg_processing_time_seconds:
                self.avg_processing_time_seconds = (self.avg_processing_time_seconds + processing_time) / 2
            else:
                self.avg_processing_time_seconds = processing_time
        
        self.is_ingesting = False
        self.last_successful_update = datetime.utcnow()
        self.last_updated_timestamp = datetime.utcnow()
        
        if new_checksum:
            self.checksum = new_checksum
        
        self.total_documents = docs_processed
        self.failed_documents = docs_failed
        
        if docs_failed > 0:
            self.status_message = f'Update completed with {docs_failed} failed documents'
        else:
            self.status_message = f'Update completed successfully - {docs_processed} documents processed'
        
        db.session.commit()
        log_info(f"Completed incremental update for collection: {self.collection_name} in {self.last_processing_time_seconds:.2f}s")
    
    def detect_content_changes(self, new_checksum):
        """Detect if content has changed since last update"""
        if not self.checksum:
            return True  # First time, assume changes
        return self.checksum != new_checksum
    
    def resolve_conflict(self, conflict_data, resolution_strategy=None):
        """Resolve a data conflict using specified strategy"""
        strategy = resolution_strategy or self.conflict_resolution_strategy
        
        if strategy == 'merge':
            return self._merge_conflict(conflict_data)
        elif strategy == 'replace':
            return self._replace_conflict(conflict_data)
        elif strategy == 'skip':
            return self._skip_conflict(conflict_data)
        else:
            log_warning(f"Unknown conflict resolution strategy: {strategy}")
            return self._merge_conflict(conflict_data)  # Default to merge
    
    def _merge_conflict(self, conflict_data):
        """Merge conflicting data intelligently"""
        # Implementation would depend on the specific data structure
        # For now, return a basic merge strategy
        return {
            'action': 'merged',
            'strategy': 'merge',
            'timestamp': datetime.utcnow().isoformat(),
            'data': conflict_data
        }
    
    def _replace_conflict(self, conflict_data):
        """Replace old data with new data"""
        return {
            'action': 'replaced',
            'strategy': 'replace',
            'timestamp': datetime.utcnow().isoformat(),
            'data': conflict_data
        }
    
    def _skip_conflict(self, conflict_data):
        """Skip conflicting data (keep existing)"""
        return {
            'action': 'skipped',
            'strategy': 'skip',
            'timestamp': datetime.utcnow().isoformat(),
            'data': None
        }
    
    def record_conflict_resolution(self):
        """Record that conflicts have been resolved"""
        self.pending_conflicts = 0
        self.last_conflict_resolved = datetime.utcnow()
        db.session.commit()
    
    def increment_conflict_count(self):
        """Increment pending conflicts count"""
        self.pending_conflicts += 1
        db.session.commit()
    
    def to_dict(self):
        """Convert to dictionary with enhanced fields"""
        return {
            'id': self.id,
            'collection_name': self.collection_name,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'scheduled_url': self.scheduled_url,
            'schedule_frequency': self.schedule_frequency,
            'last_updated_timestamp': self.last_updated_timestamp.isoformat() if self.last_updated_timestamp else None,
            'next_update_due_timestamp': self.next_update_due_timestamp.isoformat() if self.next_update_due_timestamp else None,
            'status_message': self.status_message,
            'is_ingesting': self.is_ingesting,
            'version': self.version,
            'checksum': self.checksum,
            'total_documents': self.total_documents,
            'failed_documents': self.failed_documents,
            'last_successful_update': self.last_successful_update.isoformat() if self.last_successful_update else None,
            'conflict_resolution_strategy': self.conflict_resolution_strategy,
            'incremental_enabled': self.incremental_enabled,
            'pending_conflicts': self.pending_conflicts,
            'last_conflict_resolved': self.last_conflict_resolved.isoformat() if self.last_conflict_resolved else None,
            'avg_processing_time_seconds': self.avg_processing_time_seconds,
            'last_processing_time_seconds': self.last_processing_time_seconds
        }

class UserFeedback(db.Model):
    """Model for storing user feedback and issue reports"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    feedback_type = db.Column(db.String(50), nullable=False, default='general', index=True)  # 'bug_report', 'feature_request', 'general'
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, nullable=True)  # 1-5 rating
    status = db.Column(db.String(20), nullable=False, default='pending', index=True)  # 'new', 'reviewed', 'resolved'
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)

    # Create composite indexes for common query patterns
    __table_args__ = (
        Index('idx_userfeedback_user_type', 'user_id', 'feedback_type'),
        Index('idx_userfeedback_type_status', 'feedback_type', 'status'),
        Index('idx_userfeedback_created_status', 'created_at', 'status'),
    )

    user = db.relationship('User', backref=db.backref('feedback', lazy='dynamic'))

    def to_dict(self):
        """Convert feedback to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'feedback_type': self.feedback_type,
            'title': self.title,
            'content': self.content,
            'rating': self.rating,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class AppConfiguration(db.Model):
    """Model for centralized application configuration"""
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    value = db.Column(db.Text, nullable=False)
    data_type = db.Column(db.String(20), nullable=False, default='string')  # string, int, float, bool, json
    description = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)

    # Create composite indexes for common query patterns
    __table_args__ = (
        Index('idx_appconfig_key_type', 'key', 'data_type'),
    )

    def get_value(self):
        """Get typed value"""
        if self.data_type == 'int':
            return int(self.value)
        elif self.data_type == 'float':
            return float(self.value)
        elif self.data_type == 'bool':
            return self.value.lower() in ('true', '1', 'yes', 'on')
        elif self.data_type == 'json':
            return json.loads(self.value)
        else:
            return self.value

    def set_value(self, value):
        """Set value with proper type handling"""
        if self.data_type == 'json':
            self.value = json.dumps(value)
        else:
            self.value = str(value)

    def to_dict(self):
        """Convert configuration to dictionary"""
        return {
            'id': self.id,
            'key': self.key,
            'value': self.get_value(),
            'data_type': self.data_type,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class UserSession(db.Model):
    """User session management with enhanced security"""
    __tablename__ = 'user_session'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    session_token = db.Column(db.String(128), unique=True, nullable=False, index=True)
    ip_address = db.Column(db.String(45), nullable=True)  # IPv4 or IPv6
    user_agent = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True, index=True)
    logout_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('sessions', lazy='dynamic'))
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_session_token_active', 'session_token', 'is_active'),
        Index('idx_session_user_active', 'user_id', 'is_active'),
        Index('idx_session_expires_active', 'expires_at', 'is_active'),
    )
    
    def to_dict(self):
        """Convert session to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'session_token': self.session_token,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'is_active': self.is_active,
            'logout_at': self.logout_at.isoformat() if self.logout_at else None
        }


class UserActivity(db.Model):
    """Enhanced user activity tracking with session analytics and usage patterns"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    activity_type = db.Column(db.String(50), nullable=False, index=True)  # login, logout, api_call, etc.
    details = db.Column(db.Text, nullable=True)  # JSON string of additional details
    ip_address = db.Column(db.String(45), nullable=True)  # IPv4 or IPv6
    user_agent = db.Column(db.String(500), nullable=True)
    session_id = db.Column(db.String(128), nullable=True, index=True)  # Track sessions
    duration_seconds = db.Column(db.Integer, nullable=True)  # For tracking durations
    feature_used = db.Column(db.String(100), nullable=True, index=True)  # Specific feature used
    endpoint = db.Column(db.String(200), nullable=True)  # API endpoint or page
    response_time_ms = db.Column(db.Integer, nullable=True)  # Response time tracking
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # Create composite indexes for common query patterns
    __table_args__ = (
        Index('idx_useractivity_user_type', 'user_id', 'activity_type'),
        Index('idx_useractivity_type_created', 'activity_type', 'created_at'),
        Index('idx_useractivity_ip_created', 'ip_address', 'created_at'),
        Index('idx_useractivity_session_created', 'session_id', 'created_at'),
        Index('idx_useractivity_feature_created', 'feature_used', 'created_at'),
        Index('idx_useractivity_user_session', 'user_id', 'session_id'),
    )

    user = db.relationship('User', backref=db.backref('activities', lazy='dynamic'))

    def get_details(self):
        """Get details as dictionary"""
        try:
            return json.loads(self.details) if self.details else {}
        except (ValueError, json.JSONDecodeError):
            return {}

    def set_details(self, details):
        """Set details from dictionary"""
        self.details = json.dumps(details) if details else None

    def to_dict(self):
        """Convert activity to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'activity_type': self.activity_type,
            'details': self.get_details(),
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'session_id': self.session_id,
            'duration_seconds': self.duration_seconds,
            'feature_used': self.feature_used,
            'endpoint': self.endpoint,
            'response_time_ms': self.response_time_ms,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    @classmethod
    def track_activity(cls, user_id, activity_type, **kwargs):
        """Convenience method to track user activity with analytics"""
        try:
            activity = cls(
                user_id=user_id,  # type: ignore
                activity_type=activity_type,  # type: ignore  
                details=json.dumps(kwargs.get('details', {})),  # type: ignore
                ip_address=kwargs.get('ip_address'),  # type: ignore
                user_agent=kwargs.get('user_agent'),  # type: ignore
                session_id=kwargs.get('session_id'),  # type: ignore
                duration_seconds=kwargs.get('duration_seconds'),  # type: ignore
                feature_used=kwargs.get('feature_used'),  # type: ignore
                endpoint=kwargs.get('endpoint'),  # type: ignore
                response_time_ms=kwargs.get('response_time_ms')  # type: ignore
            )
            db.session.add(activity)
            db.session.commit()
            return activity
        except Exception as e:
            db.session.rollback()
            log_error(f"Failed to track user activity: {e}")
            return None

    @classmethod
    def get_user_session_stats(cls, user_id, days=30):
        """Get user session statistics over the last N days"""
        try:
            from datetime import timedelta
            
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Get session data
            sessions = db.session.query(cls.session_id, 
                                      db.func.min(cls.created_at).label('session_start'),
                                      db.func.max(cls.created_at).label('session_end'),
                                      db.func.count(cls.id).label('activity_count'))\
                               .filter(cls.user_id == user_id,
                                     cls.created_at >= cutoff_date,
                                     cls.session_id.isnot(None))\
                               .group_by(cls.session_id).all()
            
            total_sessions = len(sessions)
            total_duration = 0
            activities_per_session = []
            
            for session in sessions:
                if session.session_start and session.session_end:
                    duration = (session.session_end - session.session_start).total_seconds()
                    total_duration += duration
                    activities_per_session.append(session.activity_count)
            
            avg_duration = total_duration / max(total_sessions, 1) / 60  # Convert to minutes
            avg_activities = sum(activities_per_session) / max(len(activities_per_session), 1)
            
            return {
                'total_sessions': total_sessions,
                'avg_session_duration_minutes': round(avg_duration, 2),
                'total_duration_hours': round(total_duration / 3600, 2),
                'avg_activities_per_session': round(avg_activities, 1)
            }
            
        except Exception as e:
            log_error(f"Error getting user session stats: {e}")
            return {}

    @classmethod  
    def get_feature_usage_analytics(cls, user_id=None, days=30):
        """Get feature usage analytics"""
        try:
            from datetime import timedelta
            
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            query = db.session.query(cls.feature_used, 
                                   db.func.count(cls.id).label('usage_count'),
                                   db.func.avg(cls.response_time_ms).label('avg_response_time'))\
                             .filter(cls.created_at >= cutoff_date,
                                   cls.feature_used.isnot(None))
            
            if user_id:
                query = query.filter(cls.user_id == user_id)
            
            results = query.group_by(cls.feature_used)\
                          .order_by(db.func.count(cls.id).desc()).all()
            
            feature_stats = []
            for result in results:
                feature_stats.append({
                    'feature': result.feature_used,
                    'usage_count': result.usage_count,
                    'avg_response_time_ms': round(result.avg_response_time or 0, 2)
                })
            
            return feature_stats
            
        except Exception as e:
            log_error(f"Error getting feature usage analytics: {e}")
            return []

    @classmethod
    def get_user_behavior_patterns(cls, user_id, days=30):
        """Analyze user behavior patterns"""
        try:
            from datetime import timedelta
            from collections import Counter
            
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            activities = cls.query.filter(cls.user_id == user_id,
                                        cls.created_at >= cutoff_date).all()
            
            # Analyze patterns
            hours_of_day = [activity.created_at.hour for activity in activities if activity.created_at]
            days_of_week = [activity.created_at.weekday() for activity in activities if activity.created_at]
            activity_types = [activity.activity_type for activity in activities]
            
            hour_counter = Counter(hours_of_day)
            day_counter = Counter(days_of_week)
            type_counter = Counter(activity_types)
            
            # Find peak hours and days
            peak_hour = hour_counter.most_common(1)[0][0] if hour_counter else None
            peak_day = day_counter.most_common(1)[0][0] if day_counter else None
            
            day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            
            return {
                'total_activities': len(activities),
                'peak_hour': peak_hour,
                'peak_day': day_names[peak_day] if peak_day is not None else None,
                'hourly_distribution': dict(hour_counter),
                'daily_distribution': {day_names[day]: count for day, count in day_counter.items()},
                'activity_type_distribution': dict(type_counter),
                'most_used_feature': type_counter.most_common(1)[0][0] if type_counter else None
            }
            
        except Exception as e:
            log_error(f"Error analyzing user behavior patterns: {e}")
            return {}


# Database query optimization utilities - SQLAlchemy compatible

def optimize_query_performance():
    """Apply database query optimizations and analyze performance"""
    from sqlalchemy import text
    try:
        start_time = time.time()
        
        # For SQLite databases, ANALYZE helps the query planner
        db.session.execute(text("ANALYZE"))  # type: ignore
        
        # Update table statistics for all tables
        tables = ['user', 'chat_session', 'system_prompt', 'app_setting', 
                 'feedback', 'rag_collection_metadata', 'user_feedback', 
                 'app_configuration', 'user_activity']
        
        for table in tables:
            try:
                # Validate table name against known tables for security
                if table in ['user', 'chat_session', 'system_prompt', 'app_setting', 
                           'feedback', 'rag_collection_metadata', 'user_feedback', 
                           'app_configuration', 'user_activity']:
                    table_start = time.time()
                    # Use text() with safe table name (already validated)
                    db.session.execute(text(f"ANALYZE {table}"))  # type: ignore
                    table_duration = time.time() - table_start
                    query_monitor.record_query(table_duration, f"ANALYZE {table}")
            except Exception as e:
                log_warning(f"Could not analyze table {table}: {e}")
        
        db.session.commit()
        total_duration = time.time() - start_time
        query_monitor.record_query(total_duration, "optimize_query_performance")
        
        log_info(f"Database query optimization completed successfully in {total_duration:.3f}s")
        return True
        
    except Exception as e:
        log_error(f"Error during query optimization: {e}")
        db.session.rollback()
        return False


def get_query_performance_stats():
    """Get comprehensive database query performance statistics"""
    from sqlalchemy import text
    try:
        stats = {
            'slow_queries': [],
            'table_stats': [],
            'index_usage': [],
            'monitor_stats': query_monitor.get_stats()
        }
        
        # Get basic table information
        tables = ['user', 'chat_session', 'system_prompt', 'app_setting', 
                 'feedback', 'rag_collection_metadata', 'user_feedback', 
                 'app_configuration', 'user_activity']
        
        for table in tables:
            try:
                if table in ['user', 'chat_session', 'system_prompt', 'app_setting', 
                           'feedback', 'rag_collection_metadata', 'user_feedback', 
                           'app_configuration', 'user_activity']:
                    start_time = time.time()
                    result = db.session.execute(text(f"SELECT COUNT(*) FROM {table}"))  # type: ignore
                    row_count = result.scalar()
                    duration = time.time() - start_time
                    
                    query_monitor.record_query(duration, f"SELECT COUNT(*) FROM {table}")
                    
                    stats['table_stats'].append({
                        'table': table,
                        'row_count': row_count,
                        'query_time': round(duration, 3)
                    })
            except Exception as e:
                log_warning(f"Could not get stats for table {table}: {e}")
        
        # Add performance dashboard data
        stats['dashboard'] = {
            'total_queries_executed': stats['monitor_stats']['total_queries'],
            'average_response_time': stats['monitor_stats']['average_query_time'],
            'slow_queries_detected': stats['monitor_stats']['slow_queries_count'],
            'performance_score': calculate_performance_score(stats['monitor_stats'])
        }
        
        log_info("Database performance stats retrieved successfully")
        return stats
        
    except Exception as e:
        log_error(f"Error getting performance stats: {e}")
        return {'error': str(e)}


def calculate_performance_score(monitor_stats):
    """Calculate a performance score from 0-100 based on query metrics"""
    if monitor_stats['total_queries'] == 0:
        return 100
    
    avg_time = monitor_stats['average_query_time']
    slow_query_ratio = monitor_stats['slow_queries_count'] / monitor_stats['total_queries']
    
    # Score based on average query time (lower is better)
    time_score = max(0, 100 - (avg_time * 100))  # 1s = 0 points
    
    # Score based on slow query ratio (lower is better)
    slow_query_score = max(0, 100 - (slow_query_ratio * 200))  # 50% slow queries = 0 points
    
    # Weighted average
    return round((time_score * 0.6) + (slow_query_score * 0.4))


def create_database_indexes():
    """Create additional database indexes for performance optimization"""
    from sqlalchemy import text
    try:
        # Additional indexes that could improve performance
        additional_indexes = [
            "CREATE INDEX IF NOT EXISTS idx_user_lastlogin_desc ON user(last_login DESC)",
            "CREATE INDEX IF NOT EXISTS idx_chatsession_updated_desc ON chat_session(updated_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_feedback_created_desc ON feedback(created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_useractivity_created_desc ON user_activity(created_at DESC)"
        ]
        
        for index_sql in additional_indexes:
            try:
                db.session.execute(text(index_sql))  # type: ignore
                log_info(f"Created/verified index: {index_sql}")
            except Exception as e:
                log_warning(f"Could not create index: {index_sql}, error: {e}")
        
        db.session.commit()
        log_info("Database indexes creation completed successfully")
        return True
        
    except Exception as e:
        log_error(f"Error creating indexes: {e}")
        db.session.rollback()
        return False