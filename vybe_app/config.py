"""
Centralized Configuration Management for Vybe AI Desktop Application.

This module provides comprehensive configuration management for the Vybe AI Desktop
Application, handling application settings, environment variables, security
configuration, and runtime parameters with validation and type safety.

The configuration system supports:
- Environment variable parsing with fallback defaults
- Security configuration with automatic key generation
- SSL/HTTPS setup and certificate management
- Database connection and performance settings
- AI model configuration and paths
- User data directory management
- Hot-reloading of configuration files
- Comprehensive validation and error handling

Key Features:
- Automatic secret key generation for production security
- Flexible database URI configuration with user data paths
- SSL certificate handling and HTTPS enforcement
- Rate limiting and security header configuration
- Platform-specific user data directory detection
- Environment-based configuration switching
- Configuration caching for performance
- Hot-reload capabilities with file system monitoring

Security Features:
- Automatic cryptographically secure key generation
- Production vs development mode detection
- SSL/TLS certificate configuration
- Security header enforcement
- Rate limiting configuration
- Session security settings

Example:
    Basic configuration usage:
    
    >>> from vybe_app.config import Config
    >>> print(f"Application version: {Config.VERSION}")
    >>> print(f"Database URI: {Config.SQLALCHEMY_DATABASE_URI}")
    >>> Config.ensure_user_data_dirs()  # Create necessary directories

Note:
    The configuration automatically adapts to the deployment environment,
    generating secure defaults in production while maintaining developer
    convenience in development mode.
"""

import os
import json
import ipaddress
import secrets
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Union
from dotenv import load_dotenv

# Import caching for configuration caching
try:
    from .utils.cache_manager import cache
    CACHE_AVAILABLE = True
except ImportError:
    # Fallback if cache is not available during initialization
    CACHE_AVAILABLE = False

# Check watchdog availability for hot-reloading feature
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False

# Application version
VYBE_VERSION = "1.2.0"

# Load environment variables
load_dotenv()

# Default system prompt for reset purposes
DEFAULT_CUSTOM_SYSTEM_PROMPT = """You are Vybe, an intelligent AI assistant. You are helpful, accurate, and concise in your responses. You aim to provide useful information while being conversational and engaging.

Key guidelines:
- Be direct and clear in your responses
- Use tools when you need additional information
- Always verify facts when possible
- Be honest about limitations in your knowledge"""

class Config:
    """
    Centralized configuration class for the Vybe AI Desktop Application.
    
    This class contains all application configuration settings, including security,
    database, AI model settings, networking, and user data management. It automatically
    handles environment variable parsing, default value assignment, and platform-specific
    configurations.
    
    The configuration class supports multiple deployment scenarios:
    - Development: Uses convenient defaults and debug settings
    - Testing: Enables test mode with isolated data directories  
    - Production: Enforces security settings and generates secure defaults
    
    Key Configuration Areas:
        - Application metadata (version, name)
        - Security settings (keys, SSL, headers)
        - Database configuration (URI, connection pooling)
        - AI model paths and settings
        - Network configuration (host, port, CORS)
        - User data and workspace directories
        - Performance and caching settings
        - Logging and monitoring configuration
    
    Attributes:
        VERSION (str): Application version string.
        APP_NAME (str): Human-readable application name.
        SECRET_KEY (str): Flask secret key for sessions and security.
        SQLALCHEMY_DATABASE_URI (str): Database connection string.
        HOST (str): Server bind address.
        PORT (int): Server port number.
        DEBUG (bool): Enable debug mode.
        VYBE_TEST_MODE (bool): Enable test mode.
    
    Security Features:
        - Automatic secret key generation in production
        - SSL certificate configuration
        - Security header enforcement
        - Rate limiting configuration
        - CORS policy management
    
    Example:
        >>> # Basic configuration access
        >>> if Config.DEBUG:
        ...     print("Running in debug mode")
        >>> 
        >>> # Ensure directories exist
        >>> Config.ensure_user_data_dirs()
        >>> 
        >>> # SSL setup
        >>> ssl_context = Config.setup_ssl_context()
    """
    
    # Application Info
    VERSION = VYBE_VERSION
    APP_NAME = "Vybe AI Assistant"
    
    # Security Configuration
    _default_secret_key = 'dev-secret-key-change-in-production'
    _raw_secret_key = os.getenv('SECRET_KEY', _default_secret_key)
    
    # Check if SECRET_KEY is still the default value and we're not in debug mode
    if _raw_secret_key == _default_secret_key:
        # Check if we're in production mode (not debug/test)
        debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() in ('true', '1', 'yes', 'on')
        test_mode = os.getenv('VYBE_TEST_MODE', 'False').lower() in ('true', '1', 'yes', 'on')
        
        if not debug_mode and not test_mode:
            # Generate a cryptographically secure random key
            SECRET_KEY = secrets.token_hex(32)
            # Log a clear warning
            logging.warning(
                "⚠️  SECURITY WARNING: Default SECRET_KEY detected in production mode. "
                "A secure random key has been auto-generated for this session. "
                "Please set a permanent SECRET_KEY environment variable for production use."
            )
        else:
            SECRET_KEY = _raw_secret_key
    else:
        SECRET_KEY = _raw_secret_key
    
    # HTTPS/SSL Configuration
    SSL_CERT_PATH = os.getenv('SSL_CERT_PATH')  # Path to SSL certificate file
    SSL_KEY_PATH = os.getenv('SSL_KEY_PATH')    # Path to SSL private key file
    FORCE_HTTPS = os.getenv('FORCE_HTTPS', 'False').lower() in ('true', '1', 'yes', 'on')
    SSL_CONTEXT = None  # Will be set based on cert/key paths
    
    # Security Headers
    SECURITY_HEADERS = {
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains; preload',
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' ws: wss:",
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        'Permissions-Policy': 'camera=(), microphone=(), geolocation=()'
    }
    
    # Rate Limiting
    RATELIMIT_STORAGE_URL = os.getenv('RATELIMIT_STORAGE_URL', 'memory://')
    RATELIMIT_DEFAULT = os.getenv('RATELIMIT_DEFAULT', '1000 per hour')
    RATELIMIT_HEADERS_ENABLED = True
    
    # Session Security
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'False').lower() in ('true', '1', 'yes', 'on')
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = int(os.getenv('SESSION_LIFETIME', '3600'))  # 1 hour default
    
    # CSRF Protection
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = int(os.getenv('CSRF_TIME_LIMIT', '3600'))  # 1 hour
    
    # Content Security
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload
    
    # Developer Settings
    VYBE_TEST_MODE = os.getenv('VYBE_TEST_MODE', 'False').lower() in ('true', '1', 'yes', 'on')
    
    # Database - Use user data directory for write permissions with optimized connection pooling
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URI', 'sqlite:///site.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_RECORD_QUERIES = True
    
    # Enhanced Database Connection Pool Settings
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': int(os.getenv('DB_POOL_SIZE', '20')),          # Base connections
        'max_overflow': int(os.getenv('DB_MAX_OVERFLOW', '30')),    # Additional connections
        'pool_pre_ping': True,                                      # Validate connections
        'pool_recycle': int(os.getenv('DB_POOL_RECYCLE', '3600')), # Recycle every hour
        'pool_timeout': int(os.getenv('DB_POOL_TIMEOUT', '30')),   # Connection timeout
        'connect_args': {
            'check_same_thread': False,  # For SQLite
            'timeout': 20                # SQLite busy timeout
        }
    }
    
    # Database Performance Monitoring
    SQLALCHEMY_SLOW_QUERY_THRESHOLD = float(os.getenv('SLOW_QUERY_THRESHOLD', '1.0'))
    SQLALCHEMY_ENABLE_POOL_EVENTS = True
    
    # Connection Pool Health Monitoring
    DB_HEALTH_CHECK_INTERVAL = int(os.getenv('DB_HEALTH_CHECK_INTERVAL', '300'))  # 5 minutes
    
    # Server Configuration
    PORT = int(os.getenv('VYBE_PORT', '8000'))
    HOST = os.getenv('VYBE_HOST', '0.0.0.0')
    
    # LLM Backend Configuration (llama-cpp-python)
    LLM_BACKEND_URL = os.getenv('LLM_BACKEND_URL', 'http://localhost:11435')
    LLM_BACKEND_TIMEOUT = int(os.getenv('LLM_BACKEND_TIMEOUT', '30'))
    # Hard minimum context tokens required for backend orchestrator/model
    REQUIRED_MIN_CONTEXT_TOKENS = int(os.getenv('VYBE_REQUIRED_MIN_CONTEXT', '32768'))
    
    # RAG Configuration - Use user data directories
    @staticmethod
    def get_user_data_dir():
        """
        Get the platform-appropriate user data directory for Vybe.
        
        This method returns the appropriate user data directory based on the
        operating system, following platform conventions for user application data.
        
        Returns:
            Path: Platform-specific user data directory path:
                 - Windows: ~/AppData/Local/Vybe AI Assistant
                 - Linux/Mac: ~/.local/share/vybe-ai-assistant
        
        Note:
            The directory is not created by this method. Use ensure_user_data_dirs()
            to create the directory structure.
        """
        if os.name == 'nt':  # Windows
            return Path(os.path.expanduser("~")) / "AppData" / "Local" / "Vybe AI Assistant"
        else:  # Linux/Mac
            return Path(os.path.expanduser("~")) / ".local" / "share" / "vybe-ai-assistant"
    
    # Class variables to track initialization states (lazy loading)
    _dirs_initialized = False
    _ssl_initialized = False
    _ssl_context_cached = None
    _config_validation_cached = None
    _config_file_watchers = {}
    _hot_reload_enabled = os.getenv('CONFIG_HOT_RELOAD', 'False').lower() in ('true', '1', 'yes', 'on')
    _config_callbacks = []
    
    @classmethod
    def ensure_user_data_dirs(cls):
        """
        Ensure user data directories exist with proper permissions.
        
        This method creates all necessary user data directories for the application,
        including workspace, logs, RAG data, and models directories. It uses
        caching to avoid repeated directory creation checks and implements
        fallback logic for permission issues.
        
        Created Directories:
            - Main user data directory (platform-specific)
            - workspace/ - User file operations and AI-generated content
            - logs/ - Application log files and debugging information
            - rag_data/ - Knowledge base and RAG collection storage
            - models/ - User-added AI model files and metadata
        
        Error Handling:
            If the primary user data directory cannot be created due to permission
            issues, the method falls back to creating directories in the current
            working directory.
        
        Note:
            This method is cached at the class level to prevent repeated I/O
            operations and improve application startup performance.
        """
        # Use class-level cache to avoid repeated directory creation checks
        if not cls._dirs_initialized:
            user_data_dir = cls.get_user_data_dir()
            workspace_dir = user_data_dir / "workspace"
            logs_dir = user_data_dir / "logs"
            rag_dir = user_data_dir / "rag_data"
            models_dir = user_data_dir / "models"  # Add models directory for user-added models
            
            # Create directories safely
            for dir_path in [user_data_dir, workspace_dir, logs_dir, rag_dir, models_dir]:
                try:
                    dir_path.mkdir(parents=True, exist_ok=True)
                except PermissionError:
                    # Fallback to current directory if user data dir not accessible
                    fallback_dir = Path.cwd() / dir_path.name
                    fallback_dir.mkdir(parents=True, exist_ok=True)
            
            # Mark as initialized to prevent repeated calls
            cls._dirs_initialized = True
            print(f"✅ User data directories initialized: {user_data_dir}")

    @classmethod 
    def get_cached_ssl_context(cls):
        """
        Get SSL context with caching to avoid repeated setup operations.
        
        This method provides a cached SSL context to prevent repeated SSL
        setup operations during application runtime. The SSL context is
        created once and reused for all subsequent requests.
        
        Returns:
            ssl.SSLContext or None: Configured SSL context if certificates
                                   are available and valid, None otherwise.
        
        Performance Features:
            - One-time SSL context creation
            - Cached result for repeated access
            - Lazy initialization pattern
        
        Example:
            >>> ssl_context = Config.get_cached_ssl_context()
            >>> if ssl_context:
            ...     app.run(ssl_context=ssl_context)
        
        Note:
            The SSL context is only created if both SSL_CERT_PATH and
            SSL_KEY_PATH are configured and the files exist.
        """
        if not cls._ssl_initialized:
            cls._ssl_context_cached = cls._setup_ssl_context_internal()
            cls._ssl_initialized = True
        return cls._ssl_context_cached

    @classmethod
    def _setup_ssl_context_internal(cls):
        """
        Internal SSL context setup with comprehensive error handling.
        
        This method handles the actual SSL context creation, certificate
        loading, and security configuration. It includes comprehensive
        error handling and validation of certificate files.
        
        Returns:
            ssl.SSLContext or None: Configured SSL context with security
                                   settings if successful, None if setup fails.
        
        SSL Security Features:
            - TLS 1.2 minimum version requirement
            - Strong cipher suite selection
            - ECDHE and DHE key exchange preference
            - Exclusion of weak ciphers (aNULL, MD5, DSS)
        
        Error Handling:
            - Validates certificate and key file existence
            - Provides detailed error messages for troubleshooting
            - Graceful fallback to non-SSL mode on failure
        
        Example:
            >>> context = Config._setup_ssl_context_internal()
            >>> if context:
            ...     print("SSL context ready for production use")
        
        Note:
            This is an internal method used by get_cached_ssl_context().
            Use the public method instead of calling this directly.
        """
        import ssl
        from pathlib import Path
        
        if not cls.SSL_CERT_PATH or not cls.SSL_KEY_PATH:
            return None
            
        cert_path = Path(cls.SSL_CERT_PATH)
        key_path = Path(cls.SSL_KEY_PATH)
        
        if not cert_path.exists() or not key_path.exists():
            print(f"Warning: SSL certificate files not found:")
            print(f"  Certificate: {cert_path} ({'exists' if cert_path.exists() else 'missing'})")
            print(f"  Key: {key_path} ({'exists' if key_path.exists() else 'missing'})")
            return None
        
        try:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(str(cert_path), str(key_path))
            
            # Security settings
            context.minimum_version = ssl.TLSVersion.TLSv1_2
            context.set_ciphers('ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS')
            
            print(f"✅ SSL context configured successfully")
            print(f"   Certificate: {cert_path}")
            print(f"   Key: {key_path}")
            
            return context
            
        except Exception as e:
            print(f"❌ Failed to setup SSL context: {e}")
            return None

    @classmethod
    def validate_configuration(cls):
        """
        Comprehensive configuration validation with caching and error reporting.
        
        This method performs thorough validation of all configuration settings
        including security, network, file system, and application-specific
        parameters. Results are cached to avoid repeated validation overhead.
        
        Returns:
            dict: Validation results dictionary containing:
                - valid (bool): Overall validation status
                - warnings (list): Non-critical configuration issues
                - errors (list): Critical configuration problems
        
        Validation Checks:
            - Secret key security assessment
            - SSL certificate file existence
            - Network configuration (IP address and port validation)
            - File system path accessibility
            - Application-specific settings
        
        Example:
            >>> result = Config.validate_configuration()
            >>> if not result['valid']:
            ...     print("Configuration errors:", result['errors'])
            >>> if result['warnings']:
            ...     print("Configuration warnings:", result['warnings'])
        
        Note:
            Results are cached at the class level to improve performance.
            Critical errors indicate configuration issues that must be
            resolved before the application can run properly.
        """
        if cls._config_validation_cached is not None:
            return cls._config_validation_cached
        
        validation_results = {
            'valid': True,
            'warnings': [],
            'errors': []
        }
        
        try:
            # Validate secret key
            if cls.SECRET_KEY == 'dev-secret-key-change-in-production':
                validation_results['warnings'].append("Using default secret key - change in production")
            
            # Validate paths
            if cls.SSL_CERT_PATH and not Path(cls.SSL_CERT_PATH).exists():
                validation_results['warnings'].append(f"SSL certificate not found: {cls.SSL_CERT_PATH}")
            
            # Validate network settings
            try:
                if cls.HOST != '0.0.0.0' and cls.HOST != '127.0.0.1':
                    ipaddress.ip_address(cls.HOST)
            except ValueError:
                validation_results['errors'].append(f"Invalid HOST IP address: {cls.HOST}")
                validation_results['valid'] = False
            
            # Validate port range
            if not (1 <= cls.PORT <= 65535):
                validation_results['errors'].append(f"Invalid PORT number: {cls.PORT}")
                validation_results['valid'] = False
            
            cls._config_validation_cached = validation_results
            
        except Exception as e:
            validation_results['errors'].append(f"Configuration validation error: {str(e)}")
            validation_results['valid'] = False
            cls._config_validation_cached = validation_results
        
        return validation_results

    @classmethod
    def reset_cache(cls):
        """Reset all cached configuration data - useful for testing"""
        cls._dirs_initialized = False
        cls._ssl_initialized = False
        cls._ssl_context_cached = None
        cls._config_validation_cached = None

    @classmethod
    def enable_hot_reload(cls, config_file_path=None):
        """Enable configuration hot reloading with file watching"""
        if not cls._hot_reload_enabled or not WATCHDOG_AVAILABLE:
            if not WATCHDOG_AVAILABLE:
                print("⚠️  watchdog not installed - configuration hot reloading disabled")
            return False
            
        try:
            import threading
            
            class ConfigFileHandler(FileSystemEventHandler):
                def __init__(self, config_class):
                    self.config_class = config_class
                    
                def on_modified(self, event):
                    file_path = str(event.src_path)
                    if not event.is_directory and (
                        file_path.endswith('.env') or 
                        file_path.endswith('.ini') or 
                        file_path.endswith('.yaml') or 
                        file_path.endswith('.yml')
                    ):
                        print(f"📝 Configuration file changed: {file_path}")
                        self.config_class._reload_configuration(file_path)
            
            # Watch .env file and config directory
            observer = Observer()
            handler = ConfigFileHandler(cls)
            
            # Watch current directory for .env files
            observer.schedule(handler, path='.', recursive=False)
            
            # Watch config directory if specified
            if config_file_path:
                config_dir = os.path.dirname(config_file_path)
                observer.schedule(handler, path=config_dir, recursive=False)
            
            observer.start()
            cls._config_file_watchers['observer'] = observer
            
            print("🔄 Configuration hot reloading enabled")
            return True
            
        except ImportError:
            print("⚠️  watchdog not installed - configuration hot reloading disabled")
            return False
        except Exception as e:
            print(f"❌ Failed to enable configuration hot reloading: {e}")
            return False

    @classmethod
    def _reload_configuration(cls, file_path):
        """Reload configuration from file and notify callbacks"""
        try:
            print(f"🔄 Reloading configuration from {file_path}")
            
            # Clear caches to force reload
            cls.reset_cache()
            
            # Reload environment variables if .env file changed
            if file_path.endswith('.env'):
                cls._reload_env_file(file_path)
            
            # Validate new configuration
            validation_result = cls.validate_configuration()
            if not validation_result['valid']:
                print("❌ Configuration validation failed after reload:")
                for error in validation_result['errors']:
                    print(f"   - {error}")
                return False
            
            # Notify registered callbacks
            for callback in cls._config_callbacks:
                try:
                    callback(cls)
                except Exception as e:
                    print(f"⚠️  Configuration reload callback failed: {e}")
            
            print("✅ Configuration reloaded successfully")
            return True
            
        except Exception as e:
            print(f"❌ Failed to reload configuration: {e}")
            return False

    @classmethod
    def _reload_env_file(cls, env_file_path):
        """Reload environment variables from .env file"""
        try:
            with open(env_file_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip().strip('"\'')
            
            # Update class attributes from new env vars
            cls.SECRET_KEY = os.getenv('SECRET_KEY', cls.SECRET_KEY)
            cls.SSL_CERT_PATH = os.getenv('SSL_CERT_PATH')
            cls.SSL_KEY_PATH = os.getenv('SSL_KEY_PATH')
            cls.FORCE_HTTPS = os.getenv('FORCE_HTTPS', str(cls.FORCE_HTTPS)).lower() in ('true', '1', 'yes', 'on')
            
        except Exception as e:
            print(f"⚠️  Failed to reload .env file: {e}")

    @classmethod
    def register_reload_callback(cls, callback):
        """Register a callback to be called when configuration is reloaded"""
        if callable(callback):
            cls._config_callbacks.append(callback)

    @classmethod  
    def disable_hot_reload(cls):
        """Disable configuration hot reloading"""
        try:
            if 'observer' in cls._config_file_watchers:
                cls._config_file_watchers['observer'].stop()
                cls._config_file_watchers['observer'].join()
                del cls._config_file_watchers['observer']
                print("🔄 Configuration hot reloading disabled")
                
        except Exception as e:
            print(f"⚠️  Error disabling configuration hot reloading: {e}")

    @staticmethod
    def get_models_directories():
        """
        Get prioritized list of directories to search for AI models.
        
        This method returns a prioritized list of directories where AI models
        can be found, including bundled models (shipped with application)
        and user-added models (installed by users).
        
        Returns:
            list: Ordered list of Path objects representing model directories:
                 1. Bundled models directory (project/models/)
                 2. User models directory (user_data/models/)
                 3. Fallback current directory models folder
        
        Directory Priority:
            - Bundled models: Pre-installed models shipped with application
            - User models: Models downloaded or added by users
            - Fallback: Current working directory models folder
        
        Features:
            - Automatic directory creation for user models
            - Graceful fallback handling for missing directories
            - Cross-platform path resolution
        
        Example:
            >>> model_dirs = Config.get_models_directories()
            >>> for directory in model_dirs:
            ...     print(f"Searching for models in: {directory}")
            ...     for model_file in directory.glob("*.gguf"):
            ...         print(f"Found model: {model_file.name}")
        
        Note:
            Directories are returned in priority order. The first directory
            with a matching model will typically be used unless specific
            model selection logic is implemented.
        """
        directories = []
        
        # First, try bundled models directory (relative to project root)
        try:
            current_file = Path(__file__).resolve()
            project_root = current_file.parent.parent  # Go up from vybe_app -> project root
            bundled_models_dir = project_root / "models"
            if bundled_models_dir.exists():
                directories.append(bundled_models_dir)
        except Exception:
            pass
        
        # Second, user models directory (for user-added models)
        try:
            user_data_dir = Config.get_user_data_dir()
            user_models_dir = user_data_dir / "models"
            user_models_dir.mkdir(parents=True, exist_ok=True)
            directories.append(user_models_dir)
        except Exception:
            pass
        
        # Fallback to current directory models folder
        if not directories:
            fallback_dir = Path.cwd() / "models"
            fallback_dir.mkdir(exist_ok=True)
            directories.append(fallback_dir)
        
        return directories
    
    # Initialize user data directories
    _user_data_dir = get_user_data_dir()
    RAG_KNOWLEDGE_BASE_PATH = os.getenv('RAG_KNOWLEDGE_BASE_PATH', str(_user_data_dir / "rag_data" / "knowledge_base"))
    RAG_VECTOR_DB_PATH = os.getenv('RAG_VECTOR_DB_PATH', str(_user_data_dir / "rag_data" / "chroma_db"))
    RAG_CHUNK_SIZE = int(os.getenv('RAG_CHUNK_SIZE', '500'))
    RAG_CHUNK_OVERLAP = int(os.getenv('RAG_CHUNK_OVERLAP', '50'))
    
    # File Management
    SECURE_WORKSPACE_PATH = os.getenv('SECURE_WORKSPACE_PATH', str(_user_data_dir / "workspace"))
    MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', '16777216'))  # 16MB
    ALLOWED_FILE_EXTENSIONS = os.getenv('ALLOWED_FILE_EXTENSIONS', '.txt,.md,.pdf,.json,.csv').split(',')
    
    # Logging Configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE_PATH = os.getenv('LOG_FILE_PATH', str(_user_data_dir / "logs" / "vybe.log"))
    LOG_MAX_BYTES = int(os.getenv('LOG_MAX_BYTES', '10485760'))  # 10MB
    LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', '5'))
    
    # Web Search Configuration
    WEB_SEARCH_TIMEOUT = int(os.getenv('WEB_SEARCH_TIMEOUT', '10'))
    WEB_SEARCH_MAX_RESULTS = int(os.getenv('WEB_SEARCH_MAX_RESULTS', '10'))
    BRAVE_SEARCH_API_KEY = os.getenv('BRAVE_SEARCH_API_KEY', '')
    
    # Session Configuration
    PERMANENT_SESSION_LIFETIME = int(os.getenv('PERMANENT_SESSION_LIFETIME', '86400'))  # 24 hours
    
    # Development Settings
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() in ('true', '1', 'yes')
    TESTING = os.getenv('TESTING', 'False').lower() in ('true', '1', 'yes')

    # Service auto-start controls (prevent confusing auto-launch of external apps)
    AUTO_START_LLM = os.getenv('VYBE_AUTO_START_LLM', 'False').lower() in ('true', '1', 'yes', 'on')
    AUTO_START_SD = os.getenv('VYBE_AUTO_START_SD', 'False').lower() in ('true', '1', 'yes', 'on')
    FIRST_LAUNCH_AUTORUN = os.getenv('VYBE_FIRST_LAUNCH_AUTORUN', 'True').lower() in ('true', '1', 'yes', 'on')  # Enable by default
    AUTO_LAUNCH_EXTERNAL_APPS = os.getenv('VYBE_AUTO_LAUNCH_EXTERNAL', 'True').lower() in ('true', '1', 'yes', 'on')
    
    @classmethod
    def get_config_dict(cls):
        """Get configuration as dictionary for display/editing"""
        if CACHE_AVAILABLE:
            # Use cache decorator if available
            return cls._get_config_dict_cached()
        else:
            return cls._get_config_dict_impl()
    
    @classmethod
    def _get_config_dict_cached(cls):
        """Cached version of get_config_dict"""
        from .utils.cache_manager import cache
        
        @cache.cached(timeout=1800, cache_name="system_data")  # Cache for 30 minutes
        def _cached_config():
            return cls._get_config_dict_impl()
        
        return _cached_config()
    
    @classmethod
    def _get_config_dict_impl(cls):
        """Implementation of get_config_dict"""
        return {
            'llm_backend_url': cls.LLM_BACKEND_URL,
            'llm_backend_timeout': cls.LLM_BACKEND_TIMEOUT,
            'required_min_context_tokens': cls.REQUIRED_MIN_CONTEXT_TOKENS,
            'rag_knowledge_base_path': cls.RAG_KNOWLEDGE_BASE_PATH,
            'rag_vector_db_path': cls.RAG_VECTOR_DB_PATH,
            'secure_workspace_path': cls.SECURE_WORKSPACE_PATH,
            'max_file_size': cls.MAX_FILE_SIZE,
            'log_level': cls.LOG_LEVEL,
            'log_file_path': cls.LOG_FILE_PATH,
            'web_search_timeout': cls.WEB_SEARCH_TIMEOUT,
            'web_search_max_results': cls.WEB_SEARCH_MAX_RESULTS,
            'permanent_session_lifetime': cls.PERMANENT_SESSION_LIFETIME
        }
    
    @classmethod
    def setup_ssl_context(cls):
        """
        Setup SSL context for HTTPS if certificates are available.
        
        This is a convenience method that delegates to get_cached_ssl_context()
        to maintain backward compatibility while leveraging caching benefits.
        
        Returns:
            ssl.SSLContext or None: Configured SSL context if certificates
                                   are available and valid, None otherwise.
        
        Example:
            >>> ssl_context = Config.setup_ssl_context()
            >>> if ssl_context:
            ...     app.run(ssl_context=ssl_context, host='0.0.0.0', port=443)
            ... else:
            ...     app.run(host='0.0.0.0', port=80)  # HTTP fallback
        
        Note:
            This method uses caching to avoid repeated SSL context creation.
            Use this method instead of directly calling SSL setup functions.
        """
        return cls.get_cached_ssl_context()
    
    @classmethod
    def generate_self_signed_cert(cls):
        """Generate a self-signed certificate for development"""
        try:
            from cryptography import x509
            from cryptography.x509.oid import NameOID
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.asymmetric import rsa
            from cryptography.hazmat.primitives import serialization
            from pathlib import Path
            import datetime
            
            # Generate private key
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
            )
            
            # Certificate details
            subject = issuer = x509.Name([
                x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Development"),
                x509.NameAttribute(NameOID.LOCALITY_NAME, "Local"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Vybe AI Assistant"),
                x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
            ])
            
            cert = x509.CertificateBuilder().subject_name(
                subject
            ).issuer_name(
                issuer
            ).public_key(
                private_key.public_key()  # type: ignore
            ).serial_number(
                x509.random_serial_number()
            ).not_valid_before(
                datetime.datetime.utcnow()
            ).not_valid_after(
                datetime.datetime.utcnow() + datetime.timedelta(days=365)
            ).add_extension(
                x509.SubjectAlternativeName([
                    x509.DNSName("localhost"),
                    x509.DNSName("127.0.0.1"),
                    x509.IPAddress(ipaddress.IPv4Address("127.0.0.1"))
                ]),
                critical=False,
            ).sign(private_key, hashes.SHA256())  # type: ignore
            
            # Create certs directory
            cert_dir = Path("certs")
            cert_dir.mkdir(exist_ok=True)
            
            # Write certificate
            cert_path = cert_dir / "vybe-cert.pem"
            with open(cert_path, "wb") as f:
                f.write(cert.public_bytes(serialization.Encoding.PEM))
            
            # Write private key
            key_path = cert_dir / "vybe-key.pem"
            with open(key_path, "wb") as f:
                f.write(private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ))
            
            print(f"✅ Self-signed certificate generated:")
            print(f"   Certificate: {cert_path}")
            print(f"   Key: {key_path}")
            print(f"   Valid for: 365 days")
            print(f"   ⚠️  This is for development only - use proper certificates in production!")
            
            # Update config
            cls.SSL_CERT_PATH = str(cert_path)
            cls.SSL_KEY_PATH = str(key_path)
            
            return cls.setup_ssl_context()
            
        except ImportError:
            print("❌ cryptography package not installed. Cannot generate self-signed certificate.")
            print("   Install with: pip install cryptography")
            return None
        except Exception as e:
            print(f"❌ Failed to generate self-signed certificate: {e}")
            return None

    @classmethod
    def validate_path(cls, path_str):
        """Validate a file system path"""
        try:
            path = Path(path_str)
            # Check if it's a valid path format
            path.resolve()
            return True, ""
        except Exception as e:
            return False, f"Invalid path: {str(e)}"
    
    @classmethod
    def validate_url(cls, url_str):
        """Validate a URL"""
        import re
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        if not url_pattern.match(url_str):
            return False, "Invalid URL format"
        return True, ""
    
    @classmethod
    def ensure_directories(cls):
        """Ensure required directories exist"""
        directories = [
            cls.RAG_KNOWLEDGE_BASE_PATH,
            cls.RAG_VECTOR_DB_PATH,
            cls.SECURE_WORKSPACE_PATH,
            os.path.dirname(cls.LOG_FILE_PATH),
            os.path.dirname(cls.SQLALCHEMY_DATABASE_URI.replace('sqlite:///', '')) if cls.SQLALCHEMY_DATABASE_URI.startswith('sqlite:///') else None
        ]
        
        for directory in directories:
            if directory:
                try:
                    os.makedirs(directory, exist_ok=True)
                except Exception as e:
                    print(f"Warning: Could not create directory {directory}: {e}")

# Path to the legacy configuration file (keeping for compatibility)
CONFIG_FILE_PATH = os.path.join(os.path.dirname(__file__), 'config.json')

def load_config():
    """Load configuration from config.json file."""
    if CACHE_AVAILABLE:
        from .utils.cache_manager import cache
        
        @cache.cached(timeout=600, cache_name="system_data")  # Cache for 10 minutes
        def _load_config_cached():
            return _load_config_impl()
        
        return _load_config_cached()
    else:
        return _load_config_impl()


def _load_config_impl():
    """Implementation of load_config"""
    try:
        if os.path.exists(CONFIG_FILE_PATH):
            with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
    return {}

def save_config(config_data):
    """Save configuration to config.json file."""
    try:
        with open(CONFIG_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False

def get_system_prompt():
    """Get the custom system prompt from config."""
    config = load_config()
    return config.get('custom_system_prompt', DEFAULT_CUSTOM_SYSTEM_PROMPT)

def set_system_prompt(prompt):
    """Set the custom system prompt in config."""
    config = load_config()
    config['custom_system_prompt'] = prompt
    return save_config(config)

def reset_system_prompt():
    """Reset system prompt to default."""
    return set_system_prompt(DEFAULT_CUSTOM_SYSTEM_PROMPT)

# Initialize default configuration
Config.ensure_directories()
