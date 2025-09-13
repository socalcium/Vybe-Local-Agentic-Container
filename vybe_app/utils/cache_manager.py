"""
Global Cache Manager for Vybe Application
Provides response caching, model caching, and performance optimization
"""

import time
import json
import hashlib
import pickle
import re
from typing import Any, Dict, Optional, Union, List, Tuple, cast
from functools import wraps
from datetime import datetime, timedelta
import threading
from collections import OrderedDict
import asyncio

from ..logger import log_info, log_warning, log_error

# Try to import Redis for advanced caching
try:
    import redis
    from redis import Redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    Redis = None
    log_warning("Redis not available, using in-memory cache only")


def sanitize_cache_key(key: str) -> str:
    """
    Sanitize cache keys to ensure they only contain safe characters.
    
    This prevents potential injection attacks and ensures Redis compatibility.
    Allowed characters: alphanumeric, underscore, hyphen, and colon.
    """
    if not key:
        return "empty_key"
    
    # Replace any character that's not alphanumeric, underscore, hyphen, or colon
    sanitized = re.sub(r'[^a-zA-Z0-9_:-]', '_', key)
    
    # Ensure the key doesn't start or end with special characters
    sanitized = sanitized.strip('_-:')
    
    # Limit key length to prevent excessively long keys
    if len(sanitized) > 250:
        # Use a hash for very long keys while preserving some readability
        prefix = sanitized[:200]
        suffix = hashlib.sha256(sanitized.encode()).hexdigest()[:16]
        sanitized = f"{prefix}_{suffix}"
    
    # If after sanitization the key is empty, provide a fallback
    if not sanitized:
        sanitized = f"key_{hashlib.sha256(key.encode()).hexdigest()[:16]}"
    
    return sanitized


class LRUCache:
    """LRU Cache with TTL support"""
    
    def __init__(self, maxsize: int = 1000, ttl: int = 300):
        try:
            self.maxsize = max(1, maxsize)  # Ensure positive maxsize
            self.ttl = max(1, ttl)  # Ensure positive ttl
            self.cache: OrderedDict = OrderedDict()
            self.timestamps: Dict[str, float] = {}
            self._lock = threading.RLock()
        except Exception as e:
            log_error(f"Error initializing LRU cache: {e}")
            # Set safe defaults
            self.maxsize = 1000
            self.ttl = 300
            self.cache = OrderedDict()
            self.timestamps = {}
            self._lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        with self._lock:
            if key in self.cache:
                # Check TTL
                if time.time() - self.timestamps[key] > self.ttl:
                    del self.cache[key]
                    del self.timestamps[key]
                    return None
                
                # Move to end (most recently used)
                self.cache.move_to_end(key)
                return self.cache[key]
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache"""
        with self._lock:
            # Remove if exists
            if key in self.cache:
                del self.cache[key]
                del self.timestamps[key]
            
            # Evict oldest if cache is full
            if len(self.cache) >= self.maxsize:
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
                del self.timestamps[oldest_key]
            
            # Add new item
            self.cache[key] = value
            self.timestamps[key] = time.time()
            return True
    
    def delete(self, key: str) -> bool:
        """Delete value from cache"""
        with self._lock:
            if key in self.cache:
                del self.cache[key]
                del self.timestamps[key]
                return True
            return False
    
    def clear(self):
        """Clear all cache entries"""
        with self._lock:
            self.cache.clear()
            self.timestamps.clear()
    
    def cleanup_expired(self):
        """Remove expired entries"""
        with self._lock:
            current_time = time.time()
            expired_keys = [
                key for key, timestamp in self.timestamps.items()
                if current_time - timestamp > self.ttl
            ]
            for key in expired_keys:
                del self.cache[key]
                del self.timestamps[key]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            return {
                'size': len(self.cache),
                'maxsize': self.maxsize,
                'ttl': self.ttl
            }


class RedisCache:
    """Redis-based cache implementation"""
    
    def __init__(self, host: str = 'localhost', port: int = 6379, db: int = 0, 
                 password: Optional[str] = None, ttl: int = 300):
        if not REDIS_AVAILABLE:
            raise RuntimeError("Redis not available")
        
        self.redis_client = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=False,  # Keep binary for pickle
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True
        )
        self.ttl = ttl
        self.prefix = "vybe_cache:"
        
        # Test connection
        try:
            self.redis_client.ping()
            log_info("Redis cache connected successfully")
        except Exception as e:
            log_error(f"Redis connection failed: {e}")
            raise
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from Redis cache"""
        try:
            sanitized_key = sanitize_cache_key(key)
            full_key = f"{self.prefix}{sanitized_key}"
            data = self.redis_client.get(full_key)
            if data is not None:
                # Cast to bytes for type safety
                data_bytes = cast(bytes, data)
                return pickle.loads(data_bytes)
            return None
        except Exception as e:
            log_error(f"Redis get error: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in Redis cache"""
        try:
            sanitized_key = sanitize_cache_key(key)
            full_key = f"{self.prefix}{sanitized_key}"
            data = pickle.dumps(value)
            expire_time = ttl or self.ttl
            result = self.redis_client.setex(full_key, expire_time, data)
            return bool(result)
        except Exception as e:
            log_error(f"Redis set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete value from Redis cache"""
        try:
            sanitized_key = sanitize_cache_key(key)
            full_key = f"{self.prefix}{sanitized_key}"
            return bool(self.redis_client.delete(full_key))
        except Exception as e:
            log_error(f"Redis delete error: {e}")
            return False
    
    def clear(self, pattern: str = "*") -> bool:
        """Clear cache entries matching pattern"""
        try:
            # Sanitize the pattern - for patterns, we allow * and ? wildcards
            sanitized_pattern = re.sub(r'[^a-zA-Z0-9_:*?-]', '_', pattern)
            full_pattern = f"{self.prefix}{sanitized_pattern}"
            # Get keys synchronously and cast to list for type safety
            keys_result = self.redis_client.keys(full_pattern)
            keys_list = cast(List[str], keys_result)
            if keys_list:
                result = self.redis_client.delete(*keys_list)
                return bool(result)
            return True
        except Exception as e:
            log_error(f"Redis clear error: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get Redis cache statistics"""
        try:
            info_result = self.redis_client.info()
            # Cast to dict for type safety
            info = cast(Dict[str, Any], info_result)
            return {
                'connected_clients': info.get('connected_clients', 0),
                'used_memory_human': info.get('used_memory_human', '0B'),
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0),
                'total_commands_processed': info.get('total_commands_processed', 0)
            }
        except Exception as e:
            log_error(f"Redis stats error: {e}")
            return {}


class CacheManager:
    """Global cache manager for Vybe application"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(CacheManager, cls).__new__(cls)
                    cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize the cache manager"""
        # Initialize redis_client attribute to ensure it always exists
        self.redis_client = None
        
        # Initialize in-memory caches
        self.memory_caches = {
            'api_responses': LRUCache(maxsize=1000, ttl=300),  # 5 minutes
            'model_data': LRUCache(maxsize=100, ttl=3600),     # 1 hour
            'user_data': LRUCache(maxsize=500, ttl=1800),      # 30 minutes
            'system_data': LRUCache(maxsize=200, ttl=600),     # 10 minutes
            'file_data': LRUCache(maxsize=300, ttl=7200),      # 2 hours
            'session_data': LRUCache(maxsize=1000, ttl=1800),  # 30 minutes
        }
        
        # Initialize Redis cache if available with retry mechanism
        self.redis_cache = None
        self.redis_status = "disabled"
        if REDIS_AVAILABLE:
            self._setup_redis_with_retry()
        
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'total_requests': 0,
            'redis_hits': 0,
            'redis_misses': 0,
            'redis_failures': 0,
            'redis_recoveries': 0
        }
        
        # Start cache cleanup thread with proper stop event
        self._stop_cleanup_event = threading.Event()
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()
        
        # Register cleanup with global cleanup system
        try:
            from run import register_cleanup_function
            register_cleanup_function(self.cleanup, "Cache manager cleanup")
        except ImportError:
            pass  # Fallback if run module not available
        
        log_info("Cache manager initialized")
    
    def _setup_redis_with_retry(self, max_retries: int = 3):
        """Setup Redis with retry mechanism and health monitoring"""
        for attempt in range(max_retries):
            try:
                test_cache = RedisCache(ttl=3600)
                # Test connection
                test_cache.redis_client.ping()
                self.redis_cache = test_cache
                self.redis_status = "connected"
                log_info(f"Redis cache initialized successfully on attempt {attempt + 1}")
                return
            except Exception as e:
                self.redis_status = f"failed_attempt_{attempt + 1}"
                if attempt == max_retries - 1:
                    log_warning(f"Redis cache initialization failed after {max_retries} attempts: {e}")
                    self.redis_status = "unavailable"
                else:
                    log_warning(f"Redis connection attempt {attempt + 1} failed: {e}, retrying...")
                    time.sleep(1)  # Brief delay between retries
    
    def _test_redis_connection(self) -> bool:
        """Test if Redis connection is still healthy"""
        if not self.redis_cache:
            return False
        try:
            self.redis_cache.redis_client.ping()
            return True
        except Exception:
            return False
    
    def _handle_redis_failure(self):
        """Handle Redis connection failure with recovery attempt"""
        if self.redis_status != "unavailable":
            log_warning("Redis connection lost, attempting recovery...")
            self.stats['redis_failures'] += 1
            self.redis_status = "reconnecting"
            
            # Try to reconnect once
            try:
                if self.redis_cache:
                    self.redis_cache.redis_client.ping()
                    self.redis_status = "connected"
                    self.stats['redis_recoveries'] += 1
                    log_info("Redis connection recovered")
                else:
                    raise Exception("Redis cache instance is None")
            except Exception:
                self.redis_cache = None
                self.redis_status = "unavailable"
                log_error("Redis connection recovery failed, disabling Redis cache")
    
    def cleanup(self):
        """Clean up resources and stop background threads"""
        try:
            # Signal cleanup thread to stop
            if hasattr(self, "_stop_cleanup_event"):
                self._stop_cleanup_event.set()
            
            # Wait for cleanup thread to finish with proper timeout
            if hasattr(self, "_cleanup_thread") and self._cleanup_thread.is_alive():
                self._cleanup_thread.join(timeout=10)  # Increased timeout
                if self._cleanup_thread.is_alive():
                    log_warning("Cache cleanup thread did not terminate gracefully")
            
            # Clear all caches
            for cache in self.memory_caches.values():
                cache.clear()
            
            # Close Redis connection if available
            if hasattr(self, 'redis_client') and self.redis_client:
                try:
                    self.redis_client.close()
                except Exception as e:
                    log_warning(f"Error closing Redis connection: {e}")
            
            log_info("Cache manager cleanup completed")
        except Exception as e:
            log_error(f"Cache manager cleanup error: {e}")
    
    def get(self, cache_name: str, key: str, use_redis: bool = False) -> Optional[Any]:
        """Get value from cache with Redis failure handling"""
        self.stats['total_requests'] += 1
        
        # Try Redis first if enabled and available
        if use_redis and self.redis_cache and self.redis_status == "connected":
            try:
                value = self.redis_cache.get(key)
                if value is not None:
                    self.stats['redis_hits'] += 1
                    self.stats['hits'] += 1
                    return value
                else:
                    self.stats['redis_misses'] += 1
            except Exception as e:
                log_warning(f"Redis get operation failed for key '{key}': {e}")
                self._handle_redis_failure()
                # Continue to memory cache fallback
        
        # Fall back to memory cache
        if cache_name in self.memory_caches:
            value = self.memory_caches[cache_name].get(key)
            if value is not None:
                self.stats['hits'] += 1
            else:
                self.stats['misses'] += 1
            return value
        
        log_warning(f"Cache '{cache_name}' not found")
        self.stats['misses'] += 1
        return None
    
    def set(self, cache_name: str, key: str, value: Any, ttl: Optional[int] = None, 
            use_redis: bool = False) -> bool:
        """Set value in cache with Redis failure handling"""
        success = False
        
        # Set in Redis if enabled and available
        if use_redis and self.redis_cache and self.redis_status == "connected":
            try:
                success = self.redis_cache.set(key, value, ttl)
            except Exception as e:
                log_warning(f"Redis set operation failed for key '{key}': {e}")
                self._handle_redis_failure()
        
        # Set in memory cache
        if cache_name in self.memory_caches:
            try:
                success = self.memory_caches[cache_name].set(key, value, ttl) or success
            except Exception as e:
                log_error(f"Memory cache set error: {e}")
        else:
            log_warning(f"Cache '{cache_name}' not found")
            return False
        
        return success
    
    def delete(self, cache_name: str, key: str, use_redis: bool = False) -> bool:
        """Delete value from cache"""
        success = False
        
        # Delete from Redis if enabled
        if use_redis and self.redis_cache:
            try:
                success = self.redis_cache.delete(key)
            except Exception as e:
                log_error(f"Redis delete error: {e}")
        
        # Delete from memory cache
        if cache_name in self.memory_caches:
            success = self.memory_caches[cache_name].delete(key) or success
        
        return success
    
    def clear(self, cache_name: Optional[str] = None, pattern: str = "*", 
              use_redis: bool = False) -> bool:
        """Clear cache or all caches"""
        try:
            if cache_name:
                if cache_name in self.memory_caches:
                    self.memory_caches[cache_name].clear()
                    log_info(f"Cleared memory cache: {cache_name}")
                else:
                    log_warning(f"Memory cache '{cache_name}' not found")
                    return False
                
                if use_redis and self.redis_cache:
                    try:
                        self.redis_cache.clear(pattern)
                        log_info(f"Cleared Redis cache pattern: {pattern}")
                    except Exception as e:
                        log_error(f"Redis clear error: {e}")
            else:
                # Clear all caches
                for name in self.memory_caches:
                    self.memory_caches[name].clear()
                
                if use_redis and self.redis_cache:
                    try:
                        self.redis_cache.clear()
                    except Exception as e:
                        log_error(f"Redis clear all error: {e}")
                
                log_info("Cleared all caches")
            
            return True
        except Exception as e:
            log_error(f"Cache clear error: {e}")
            return False
    
    def invalidate_pattern(self, pattern: str, use_redis: bool = False) -> int:
        """Invalidate cache entries matching pattern"""
        invalidated_count = 0
        
        # Invalidate memory caches (simple key matching)
        for cache_name, cache in self.memory_caches.items():
            with cache._lock:
                keys_to_remove = [
                    key for key in cache.cache.keys()
                    if pattern in key
                ]
                for key in keys_to_remove:
                    cache.delete(key)
                    invalidated_count += 1
        
        # Invalidate Redis cache
        if use_redis and self.redis_cache:
            try:
                if self.redis_cache.clear(pattern):
                    invalidated_count += 1
            except Exception as e:
                log_error(f"Redis pattern invalidation error: {e}")
        
        log_info(f"Invalidated {invalidated_count} cache entries matching pattern: {pattern}")
        return invalidated_count
    
    def invalidate_cache(self, pattern: str = '*', use_redis: bool = False) -> int:
        """Invalidate cache entries - alias for invalidate_pattern"""
        return self.invalidate_pattern(pattern, use_redis)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics with Redis status"""
        memory_stats = {
            name: cache.get_stats()
            for name, cache in self.memory_caches.items()
        }
        
        redis_stats = None
        if self.redis_cache and self.redis_status == "connected":
            try:
                redis_stats = self.redis_cache.get_stats()
            except Exception as e:
                log_warning(f"Redis stats error: {e}")
                self._handle_redis_failure()
        
        return {
            'memory_caches': memory_stats,
            'redis_cache': redis_stats,
            'redis_status': self.redis_status,
            'redis_available': REDIS_AVAILABLE,
            'redis_connected': self.redis_cache is not None and self.redis_status == "connected",
            'stats': self.stats.copy()
        }
    
    def retry_redis_connection(self) -> bool:
        """Manually retry Redis connection"""
        if not REDIS_AVAILABLE:
            log_info("Redis library not available")
            return False
        
        log_info("Manually retrying Redis connection...")
        self._setup_redis_with_retry(max_retries=1)
        return self.redis_status == "connected"
    
    def get_redis_status(self) -> Dict[str, Any]:
        """Get detailed Redis status information"""
        return {
            'status': self.redis_status,
            'available': REDIS_AVAILABLE,
            'connected': self.redis_cache is not None and self.redis_status == "connected",
            'failures': self.stats.get('redis_failures', 0),
            'recoveries': self.stats.get('redis_recoveries', 0),
            'hits': self.stats.get('redis_hits', 0),
            'misses': self.stats.get('redis_misses', 0)
        }
    
    def _cleanup_loop(self):
        """Background cleanup loop"""
        # Use stop event for graceful shutdown
        self._stop_cleanup_event = getattr(self, "_stop_cleanup_event", threading.Event())
        
        while not self._stop_cleanup_event.is_set():
            try:
                # Cleanup expired entries from memory caches
                for cache in self.memory_caches.values():
                    cache.cleanup_expired()
                
                # Wait for cleanup interval or stop signal
                self._stop_cleanup_event.wait(300)  # Cleanup every 5 minutes
            except Exception as e:
                log_error(f"Cache cleanup error: {e}")
                # Wait shorter time on error but remain interruptible
                self._stop_cleanup_event.wait(60)


# Query cache decorator specifically for database operations
def query_cache(ttl: int = 300, cache_name: str = "query_cache"):
    """
    Decorator for caching database query results
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_manager = get_cache_manager()
            
            # Generate cache key from function name and arguments
            func_name = f"{func.__module__}.{func.__name__}"
            
            # Create a stable key from arguments
            key_parts = [func_name]
            
            # Add positional args (skip 'self' if present)
            start_idx = 1 if args and hasattr(args[0], '__dict__') else 0
            for i, arg in enumerate(args[start_idx:], start_idx):
                if hasattr(arg, '__dict__'):
                    # For objects, use class name and id
                    key_parts.append(f"{arg.__class__.__name__}_{id(arg)}")
                else:
                    key_parts.append(str(arg))
            
            # Add keyword arguments
            for k, v in sorted(kwargs.items()):
                key_parts.append(f"{k}={v}")
            
            cache_key = hashlib.md5("|".join(key_parts).encode()).hexdigest()
            
            # Try to get from cache first
            cached_result = cache_manager.get(cache_name, cache_key)
            if cached_result is not None:
                log_info(f"Query cache hit for {func_name}")
                return cached_result
            
            # Execute function and cache result
            log_info(f"Query cache miss for {func_name}, executing...")
            result = func(*args, **kwargs)
            
            # Only cache non-None results
            if result is not None:
                cache_manager.set(cache_name, cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator


def invalidate_query_cache(func_name: Optional[str] = None):
    """
    Invalidate query cache entries, optionally for specific function
    """
    cache_manager = get_cache_manager()
    
    # Clear the query cache from memory
    if "query_cache" in cache_manager.memory_caches:
        cache_manager.memory_caches["query_cache"].clear()
    
    # Clear from Redis if available
    if cache_manager.redis_cache:
        try:
            if func_name:
                pattern = f"{cache_manager.redis_cache.prefix}query_cache:*{func_name}*"
            else:
                pattern = f"{cache_manager.redis_cache.prefix}query_cache:*"
            
            keys_result = cache_manager.redis_cache.redis_client.keys(pattern)
            keys_list = cast(List[str], keys_result)
            if keys_list:
                cache_manager.redis_cache.redis_client.delete(*keys_list)
                return len(keys_list)
        except Exception as e:
            log_warning(f"Failed to invalidate Redis query cache: {e}")
    
    return 1  # Indicate cache was cleared


# Enhanced cache decorator for function results
def cached(timeout: int = 3600, cache_name: str = "function_cache", use_redis: bool = False):
    """
    Enhanced decorator to cache function results with configurable timeout
    
    Usage:
        @cache.cached(timeout=3600)  # Cache for 1 hour
        def expensive_function():
            return some_expensive_operation()
    
    Args:
        timeout: Cache timeout in seconds (default: 3600 = 1 hour)
        cache_name: Name of the cache bucket to use (default: "function_cache")
        use_redis: Whether to use Redis cache if available (default: False)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            func_name = f"{func.__module__}.{func.__qualname__}"
            key_parts = [func_name]
            
            # Handle positional arguments (skip 'self' if it's a method)
            start_idx = 1 if args and hasattr(args[0], '__dict__') else 0
            for arg in args[start_idx:]:
                if hasattr(arg, '__dict__'):
                    # For objects, use class name and a representative hash
                    key_parts.append(f"{arg.__class__.__name__}_{hash(str(vars(arg)) if vars(arg) else id(arg))}")
                else:
                    key_parts.append(str(arg))
            
            # Handle keyword arguments
            for k, v in sorted(kwargs.items()):
                key_parts.append(f"{k}={v}")
            
            # Create stable cache key
            cache_key_str = "|".join(key_parts)
            cache_key = hashlib.sha256(cache_key_str.encode()).hexdigest()[:32]
            
            # Try to get from cache
            cache_manager = get_cache_manager()
            cached_result = cache_manager.get(cache_name, cache_key, use_redis)
            
            if cached_result is not None:
                log_info(f"Cache hit for {func_name} (key: {cache_key[:8]}...)")
                return cached_result
            
            # Execute function and cache result
            log_info(f"Cache miss for {func_name}, executing and caching...")
            try:
                result = func(*args, **kwargs)
                # Only cache non-None results
                if result is not None:
                    cache_manager.set(cache_name, cache_key, result, timeout, use_redis)
                return result
            except Exception as e:
                log_error(f"Error executing cached function {func_name}: {e}")
                raise
        return wrapper
    return decorator


# Legacy cache decorator for backward compatibility
def legacy_cached(cache_name: str, ttl: Optional[int] = None, use_redis: bool = False):
    """Legacy decorator to cache function results (for backward compatibility)"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            key_parts = [func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
            cache_key = hashlib.md5("|".join(key_parts).encode()).hexdigest()
            
            # Try to get from cache
            cache_manager = CacheManager()
            cached_result = cache_manager.get(cache_name, cache_key, use_redis)
            
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache_manager.set(cache_name, cache_key, result, ttl, use_redis)
            
            return result
        return wrapper
    return decorator


# Async cache decorator
def async_cached(cache_name: str, ttl: Optional[int] = None, use_redis: bool = False):
    """Decorator to cache async function results"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            key_parts = [func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
            cache_key = hashlib.md5("|".join(key_parts).encode()).hexdigest()
            
            # Try to get from cache
            cache_manager = CacheManager()
            cached_result = cache_manager.get(cache_name, cache_key, use_redis)
            
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            cache_manager.set(cache_name, cache_key, result, ttl, use_redis)
            
            return result
        return wrapper
    return decorator


# Thread-safe singleton cache manager instance
_cache_manager: Optional[CacheManager] = None
_cache_manager_lock = threading.Lock()


def get_cache_manager() -> CacheManager:
    """Get thread-safe singleton cache manager instance"""
    global _cache_manager
    if _cache_manager is None:
        with _cache_manager_lock:
            # Double-check locking pattern
            if _cache_manager is None:
                _cache_manager = CacheManager()
    return _cache_manager


def init_cache_manager() -> CacheManager:
    """Initialize thread-safe singleton cache manager"""
    return get_cache_manager()


def cleanup_cache_manager():
    """Clean up the global cache manager instance"""
    global _cache_manager
    if _cache_manager is not None:
        _cache_manager.cleanup()
        _cache_manager = None


# Standalone functions for easy importing
def invalidate_cache(pattern: str = '*', use_redis: bool = False) -> int:
    """Invalidate cache entries - standalone function"""
    cache_mgr = get_cache_manager()
    return cache_mgr.invalidate_cache(pattern, use_redis)


def clear_cache(use_redis: bool = False) -> bool:
    """Clear all caches - standalone function"""
    cache_mgr = get_cache_manager()
    return cache_mgr.clear(use_redis=use_redis)


def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics - standalone function"""
    cache_mgr = get_cache_manager()
    return cache_mgr.get_stats()


# Cache invalidation patterns and strategies
CACHE_INVALIDATION_PATTERNS = {
    'user': {
        'pattern': '*user*',
        'triggers': ['user_update', 'user_delete', 'login', 'logout'],
        'scope': ['query_cache', 'user_data']
    },
    'session': {
        'pattern': '*session*',
        'triggers': ['session_end', 'session_update'],
        'scope': ['session_data', 'api_responses']
    },
    'model': {
        'pattern': '*model*',
        'triggers': ['model_change', 'model_update'],
        'scope': ['model_data', 'api_responses']
    },
    'system': {
        'pattern': '*system*',
        'triggers': ['config_change', 'system_restart'],
        'scope': ['system_data']
    }
}


def invalidate_cache_by_event(event_type: str, entity_id: Optional[str] = None) -> int:
    """
    Invalidate cache based on application events
    """
    cache_manager = get_cache_manager()
    total_invalidated = 0
    
    for pattern_name, config in CACHE_INVALIDATION_PATTERNS.items():
        if event_type in config['triggers']:
            pattern = config['pattern']
            if entity_id:
                pattern = f"*{entity_id}*"
            
            for scope in config['scope']:
                try:
                    if scope in cache_manager.memory_caches:
                        cache_manager.memory_caches[scope].clear()
                        total_invalidated += 1
                        log_info(f"Invalidated {scope} cache for event {event_type}")
                        
                    # Also clear from Redis if available
                    if cache_manager.redis_cache:
                        redis_pattern = f"{cache_manager.redis_cache.prefix}{scope}:{pattern}"
                        keys_result = cache_manager.redis_cache.redis_client.keys(redis_pattern)
                        keys_list = cast(List[str], keys_result)
                        if keys_list:
                            cache_manager.redis_cache.redis_client.delete(*keys_list)
                            total_invalidated += len(keys_list)
                            
                except Exception as e:
                    log_warning(f"Failed to invalidate {scope} cache for {event_type}: {e}")
    
    return total_invalidated


# Global cache instance for easy access
class Cache:
    """Global cache instance with decorator methods"""
    
    @staticmethod
    def cached(timeout: int = 3600, cache_name: str = "function_cache", use_redis: bool = False):
        """
        Decorator to cache function results
        
        Usage:
            from vybe_app.utils.cache_manager import cache
            
            @cache.cached(timeout=3600)
            def get_available_models():
                return expensive_model_query()
        """
        return cached(timeout=timeout, cache_name=cache_name, use_redis=use_redis)
    
    @staticmethod
    def invalidate(pattern: str = '*', use_redis: bool = False) -> int:
        """Invalidate cache entries matching pattern"""
        return invalidate_cache(pattern, use_redis)
    
    @staticmethod
    def clear(use_redis: bool = False) -> bool:
        """Clear all caches"""
        return clear_cache(use_redis)
    
    @staticmethod
    def stats() -> Dict[str, Any]:
        """Get cache statistics"""
        return get_cache_stats()


# Global cache instance
cache = Cache()


def schedule_cache_cleanup():
    """
    Schedule automatic cache cleanup for expired entries
    """
    import threading
    import time
    
    def cleanup_worker():
        while True:
            try:
                cache_manager = get_cache_manager()
                
                # Clean up expired entries from memory caches
                for cache_name, cache_obj in cache_manager.memory_caches.items():
                    if hasattr(cache_obj, 'cleanup_expired'):
                        cache_obj.cleanup_expired()
                
                # Update statistics
                cache_manager.stats['total_cleanups'] = cache_manager.stats.get('total_cleanups', 0) + 1
                
                log_info("Cache cleanup completed")
                
            except Exception as e:
                log_error(f"Cache cleanup failed: {e}")
            
            # Sleep for 5 minutes
            time.sleep(300)
    
    cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
    cleanup_thread.start()
    log_info("Cache cleanup scheduler started")
