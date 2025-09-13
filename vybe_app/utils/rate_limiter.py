#!/usr/bin/env python3
"""
Advanced Rate Limiting and Throttling System for Vybe AI Desktop Application
Provides sophisticated rate limiting, traffic shaping, and API protection
"""

import time
import threading
import sqlite3
import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union, Callable, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
from functools import wraps
from flask import request, jsonify, g, current_app
import logging
import ipaddress
from pathlib import Path

from .error_handling import ApplicationError, ErrorCode

logger = logging.getLogger(__name__)


@dataclass
class RateLimit:
    """Rate limit configuration"""
    requests: int  # Number of requests allowed
    window: int    # Time window in seconds
    burst: Optional[int] = None  # Burst allowance
    reset_time: Optional[datetime] = None
    
    def __post_init__(self):
        if self.burst is None:
            self.burst = max(1, self.requests // 10)  # 10% burst by default


@dataclass
class RateLimitRule:
    """Rate limiting rule with conditions"""
    name: str
    rate_limit: RateLimit
    endpoints: Optional[List[str]] = None  # Specific endpoints
    methods: Optional[List[str]] = None    # HTTP methods
    user_types: Optional[List[str]] = None  # User types/roles
    ip_ranges: Optional[List[str]] = None   # IP ranges
    headers: Optional[Dict[str, str]] = None  # Required headers
    priority: int = 0  # Higher priority rules are checked first
    
    def matches(self, endpoint: str, method: str, user_type: Optional[str] = None,
               ip_address: Optional[str] = None, headers: Optional[Dict[str, str]] = None) -> bool:
        """Check if this rule matches the current request"""
        
        # Check endpoints
        if self.endpoints and endpoint not in self.endpoints:
            return False
        
        # Check methods
        if self.methods and method not in self.methods:
            return False
        
        # Check user types
        if self.user_types and user_type not in self.user_types:
            return False
        
        # Check IP ranges
        if self.ip_ranges and ip_address:
            ip_match = False
            for ip_range in self.ip_ranges:
                try:
                    if ipaddress.ip_address(ip_address) in ipaddress.ip_network(ip_range, strict=False):
                        ip_match = True
                        break
                except (ipaddress.AddressValueError, ipaddress.NetmaskValueError):
                    if ip_range == ip_address:  # Exact match
                        ip_match = True
                        break
            
            if not ip_match:
                return False
        
        # Check headers
        if self.headers and headers:
            for header_name, header_value in self.headers.items():
                if headers.get(header_name) != header_value:
                    return False
        
        return True


class TokenBucket:
    """Token bucket algorithm implementation for rate limiting using integer-based calculations"""
    
    def __init__(self, capacity: int, refill_rate: float, burst_capacity: Optional[int] = None):
        self.capacity = capacity
        # Convert refill rate to tokens per millisecond (scaled by 1000)
        self.refill_rate_scaled = int(refill_rate * 1000)  # tokens per second * 1000
        self.burst_capacity = burst_capacity or capacity
        # Use scaled tokens (multiplied by 1000 to avoid floating point)
        self.tokens_scaled = capacity * 1000
        self.last_refill_ms = int(time.time() * 1000)  # milliseconds
        self._lock = threading.Lock()
    
    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens from the bucket"""
        with self._lock:
            now_ms = int(time.time() * 1000)
            
            # Refill tokens based on elapsed time (in milliseconds)
            elapsed_ms = now_ms - self.last_refill_ms
            tokens_to_add = (elapsed_ms * self.refill_rate_scaled) // 1000  # Convert back from scaled
            
            self.tokens_scaled = min(
                self.burst_capacity * 1000,  # Convert to scaled
                self.tokens_scaled + tokens_to_add
            )
            self.last_refill_ms = now_ms
            
            # Check if we have enough tokens (convert requested tokens to scaled)
            tokens_needed_scaled = tokens * 1000
            if self.tokens_scaled >= tokens_needed_scaled:
                self.tokens_scaled -= tokens_needed_scaled
                return True
            
            return False
    
    def get_wait_time(self, tokens: int = 1) -> float:
        """Get the time to wait before tokens are available"""
        with self._lock:
            tokens_needed_scaled = tokens * 1000
            if self.tokens_scaled >= tokens_needed_scaled:
                return 0.0
            
            # Calculate how many scaled tokens we need
            deficit_scaled = tokens_needed_scaled - self.tokens_scaled
            
            # Convert back to seconds: deficit_scaled / (refill_rate_scaled / 1000)
            wait_time_ms = (deficit_scaled * 1000) // self.refill_rate_scaled
            return wait_time_ms / 1000.0  # Convert to seconds


class SlidingWindowCounter:
    """Sliding window counter for precise rate limiting"""
    
    def __init__(self, window_size: int, bucket_count: int = 60):
        self.window_size = window_size
        self.bucket_count = bucket_count
        self.bucket_duration = window_size / bucket_count
        self.buckets = defaultdict(int)
        self._lock = threading.Lock()
    
    def add_request(self, timestamp: Optional[float] = None) -> int:
        """Add a request and return current count"""
        if timestamp is None:
            timestamp = time.time()
        
        with self._lock:
            # Clean old buckets
            self._cleanup_old_buckets(timestamp)
            
            # Add to current bucket
            bucket_key = int(timestamp // self.bucket_duration)
            self.buckets[bucket_key] += 1
            
            # Return total count in window
            return self._get_count_in_window(timestamp)
    
    def get_count(self, timestamp: Optional[float] = None) -> int:
        """Get current count in the window"""
        if timestamp is None:
            timestamp = time.time()
        
        with self._lock:
            self._cleanup_old_buckets(timestamp)
            return self._get_count_in_window(timestamp)
    
    def _cleanup_old_buckets(self, timestamp: float):
        """Remove buckets outside the window"""
        cutoff_bucket = int((timestamp - self.window_size) // self.bucket_duration)
        keys_to_remove = [key for key in self.buckets.keys() if key <= cutoff_bucket]
        
        for key in keys_to_remove:
            del self.buckets[key]
    
    def _get_count_in_window(self, timestamp: float) -> int:
        """Get total count in the current window"""
        window_start = timestamp - self.window_size
        start_bucket = int(window_start // self.bucket_duration)
        
        total = 0
        for bucket_key, count in self.buckets.items():
            if bucket_key > start_bucket:
                total += count
        
        return total


class RateLimitTracker:
    """Track rate limits for different keys (IP, user, API key, etc.)"""
    
    def __init__(self, storage_backend: str = "memory"):
        self.storage_backend = storage_backend
        self.memory_trackers: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self.db_path = "instance/rate_limits.db"
        self._lock = threading.Lock()
        
        if storage_backend == "database":
            self._setup_database()
    
    def _setup_database(self):
        """Setup SQLite database for persistent rate limiting"""
        try:
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS rate_limits (
                        key_hash TEXT PRIMARY KEY,
                        key_type TEXT NOT NULL,
                        key_value TEXT NOT NULL,
                        rule_name TEXT NOT NULL,
                        request_count INTEGER NOT NULL,
                        window_start INTEGER NOT NULL,
                        last_request INTEGER NOT NULL,
                        burst_used INTEGER DEFAULT 0,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_rate_limits_key_hash 
                    ON rate_limits(key_hash)
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_rate_limits_window 
                    ON rate_limits(window_start)
                """)
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to setup rate limit database: {e}")
            self.storage_backend = "memory"  # Fallback to memory
    
    def get_rate_limit_status(self, key: str, rule: RateLimitRule) -> Dict[str, Any]:
        """Get current rate limit status for a key"""
        
        if self.storage_backend == "memory":
            return self._get_memory_status(key, rule)
        else:
            return self._get_database_status(key, rule)
    
    def _get_memory_status(self, key: str, rule: RateLimitRule) -> Dict[str, Any]:
        """Get rate limit status from memory storage"""
        
        with self._lock:
            key_hash = hashlib.sha256(f"{key}:{rule.name}".encode()).hexdigest()
            
            if key_hash not in self.memory_trackers:
                # Initialize new tracker
                tracker = SlidingWindowCounter(rule.rate_limit.window)
                
                self.memory_trackers[key_hash] = {
                    'tracker': tracker,
                    'rule': rule,
                    'created_at': time.time()
                }
            
            tracker_data = self.memory_trackers[key_hash]
            tracker = tracker_data['tracker']
            
            if isinstance(tracker, SlidingWindowCounter):
                current_count = tracker.add_request()
                allowed = current_count <= rule.rate_limit.requests
                remaining = max(0, rule.rate_limit.requests - current_count)
                
                return {
                    'allowed': allowed,
                    'remaining': remaining,
                    'reset_time': time.time() + rule.rate_limit.window,
                    'wait_time': 0 if allowed else rule.rate_limit.window,
                    'limit': rule.rate_limit.requests,
                    'window': rule.rate_limit.window,
                    'current_count': current_count
                }
            
            # Fallback return
            return {
                'allowed': True,
                'remaining': rule.rate_limit.requests,
                'reset_time': time.time() + rule.rate_limit.window,
                'wait_time': 0,
                'limit': rule.rate_limit.requests,
                'window': rule.rate_limit.window
            }
    
    def _get_database_status(self, key: str, rule: RateLimitRule) -> Dict[str, Any]:
        """Get rate limit status from database storage"""
        
        try:
            key_hash = hashlib.sha256(f"{key}:{rule.name}".encode()).hexdigest()
            now = int(time.time())
            window_start = now - rule.rate_limit.window
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT request_count, window_start, burst_used
                    FROM rate_limits 
                    WHERE key_hash = ? AND window_start > ?
                """, (key_hash, window_start))
                
                result = cursor.fetchone()
                
            if result:
                current_count, db_window_start, burst_used = result
                
                # Check if we need to reset the window
                if now - db_window_start >= rule.rate_limit.window:
                    current_count = 0
                    burst_used = 0
                    db_window_start = now
            
            else:
                current_count = 0
                burst_used = 0
                db_window_start = now
            
            # Check rate limit
            allowed = current_count < rule.rate_limit.requests
            
            # Check burst limit
            if not allowed and rule.rate_limit.burst and burst_used < rule.rate_limit.burst:
                allowed = True
                burst_used += 1
            
            if allowed:
                current_count += 1
            
            # Update database
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO rate_limits 
                    (key_hash, key_type, key_value, rule_name, request_count, 
                     window_start, last_request, burst_used, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    key_hash, 'generic', key, rule.name, current_count,
                    db_window_start, now, burst_used, datetime.utcnow()
                ))
                
                conn.commit()
            
            remaining = max(0, rule.rate_limit.requests - current_count)
            reset_time = db_window_start + rule.rate_limit.window
            
            return {
                'allowed': allowed,
                'remaining': remaining,
                'reset_time': reset_time,
                'wait_time': max(0, reset_time - now) if not allowed else 0,
                'limit': rule.rate_limit.requests,
                'window': rule.rate_limit.window,
                'current_count': current_count,
                'burst_used': burst_used
            }
                
        except Exception as e:
            logger.error(f"Database rate limit check failed: {e}")
            # Fallback to allowing the request
            return {
                'allowed': True,
                'remaining': rule.rate_limit.requests,
                'reset_time': time.time() + rule.rate_limit.window,
                'wait_time': 0,
                'limit': rule.rate_limit.requests,
                'window': rule.rate_limit.window
            }


class AdvancedRateLimiter:
    """Advanced rate limiter with multiple strategies and rules"""
    
    def __init__(self, storage_backend: str = "memory"):
        self.rules: List[RateLimitRule] = []
        self.tracker = RateLimitTracker(storage_backend)
        self.global_stats = defaultdict(int)
        self.whitelist_ips: set = set()
        self.blacklist_ips: set = set()
        self._setup_default_rules()
    
    def _setup_default_rules(self):
        """Setup default rate limiting rules"""
        
        # Default API rate limit
        default_rule = RateLimitRule(
            name="default_api",
            rate_limit=RateLimit(requests=100, window=3600, burst=20),  # 100/hour with 20 burst
            priority=1
        )
        
        # Strict rate limit for auth endpoints
        auth_rule = RateLimitRule(
            name="auth_strict",
            rate_limit=RateLimit(requests=5, window=300, burst=2),  # 5/5min with 2 burst
            endpoints=['/api/auth/login', '/api/auth/register', '/api/auth/reset-password'],
            priority=10
        )
        
        # AI model inference rate limit
        ai_rule = RateLimitRule(
            name="ai_models",
            rate_limit=RateLimit(requests=20, window=3600, burst=5),  # 20/hour with 5 burst
            endpoints=['/api/ai/chat', '/api/ai/completion', '/api/ai/embedding'],
            priority=5
        )
        
        # File upload rate limit
        upload_rule = RateLimitRule(
            name="file_upload",
            rate_limit=RateLimit(requests=10, window=3600, burst=3),  # 10/hour with 3 burst
            methods=['POST', 'PUT'],
            endpoints=['/api/files/upload', '/api/models/upload'],
            priority=7
        )
        
        self.add_rule(default_rule)
        self.add_rule(auth_rule)
        self.add_rule(ai_rule)
        self.add_rule(upload_rule)
    
    def add_rule(self, rule: RateLimitRule):
        """Add a rate limiting rule"""
        self.rules.append(rule)
        # Sort by priority (higher priority first)
        self.rules.sort(key=lambda r: r.priority, reverse=True)
        logger.info(f"Added rate limit rule: {rule.name}")
    
    def remove_rule(self, rule_name: str):
        """Remove a rate limiting rule"""
        self.rules = [r for r in self.rules if r.name != rule_name]
        logger.info(f"Removed rate limit rule: {rule_name}")
    
    def add_to_whitelist(self, ip_address: str):
        """Add IP to whitelist (bypasses rate limits)"""
        self.whitelist_ips.add(ip_address)
        logger.info(f"Added IP to whitelist: {ip_address}")
    
    def add_to_blacklist(self, ip_address: str):
        """Add IP to blacklist (blocks all requests)"""
        self.blacklist_ips.add(ip_address)
        logger.info(f"Added IP to blacklist: {ip_address}")
    
    def check_rate_limit(self, key: str, endpoint: Optional[str] = None, method: str = "GET",
                        user_type: Optional[str] = None, ip_address: Optional[str] = None,
                        headers: Optional[Dict[str, str]] = None) -> Tuple[bool, Dict[str, Any]]:
        """Check if request is allowed under rate limits"""
        
        # Check blacklist
        if ip_address and ip_address in self.blacklist_ips:
            return False, {
                'error': 'IP address is blacklisted',
                'retry_after': None
            }
        
        # Check whitelist
        if ip_address and ip_address in self.whitelist_ips:
            return True, {'whitelisted': True}
        
        # Find matching rule
        matching_rule = None
        for rule in self.rules:
            if rule.matches(endpoint or '', method, user_type, ip_address, headers):
                matching_rule = rule
                break
        
        if not matching_rule:
            # No matching rule, allow by default
            return True, {'rule': 'none'}
        
        # Check rate limit with the matching rule
        status = self.tracker.get_rate_limit_status(key, matching_rule)
        
        # Update global stats
        self.global_stats['total_requests'] += 1
        if not status['allowed']:
            self.global_stats['blocked_requests'] += 1
        
        if status['allowed']:
            return True, {
                'rule': matching_rule.name,
                'remaining': status['remaining'],
                'reset_time': status['reset_time'],
                'limit': status['limit']
            }
        else:
            return False, {
                'rule': matching_rule.name,
                'error': 'Rate limit exceeded',
                'retry_after': status['wait_time'],
                'reset_time': status['reset_time'],
                'limit': status['limit']
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiting statistics"""
        return {
            'global_stats': dict(self.global_stats),
            'active_rules': len(self.rules),
            'whitelist_count': len(self.whitelist_ips),
            'blacklist_count': len(self.blacklist_ips),
            'rules': [
                {
                    'name': rule.name,
                    'requests': rule.rate_limit.requests,
                    'window': rule.rate_limit.window,
                    'priority': rule.priority
                }
                for rule in self.rules
            ]
        }


# Global rate limiter instance
rate_limiter = AdvancedRateLimiter()


def apply_rate_limit(key_func: Optional[Callable] = None, 
                    rule_name: Optional[str] = None,
                    bypass_conditions: Optional[List[Callable]] = None):
    """Decorator to apply rate limiting to Flask routes"""
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Check bypass conditions
            if bypass_conditions:
                for condition in bypass_conditions:
                    if condition():
                        return func(*args, **kwargs)
            
            # Generate rate limit key
            if key_func:
                key = key_func()
            else:
                # Default key generation
                key = get_client_ip()
                if hasattr(g, 'current_user') and g.current_user:
                    key = f"user:{getattr(g.current_user, 'id', 'anonymous')}"
            
            # Check rate limit
            allowed, info = rate_limiter.check_rate_limit(
                key=key,
                endpoint=request.endpoint or '',
                method=request.method,
                ip_address=get_client_ip(),
                headers=dict(request.headers)
            )
            
            if not allowed:
                response = jsonify({
                    'error': True,
                    'code': ErrorCode.RATE_LIMIT_EXCEEDED,
                    'message': info.get('error', 'Rate limit exceeded'),
                    'retry_after': info.get('retry_after'),
                    'reset_time': info.get('reset_time')
                })
                
                if info.get('retry_after'):
                    response.headers['Retry-After'] = str(int(info['retry_after']))
                
                return response, 429
            
            # Add rate limit headers to response
            response = func(*args, **kwargs)
            
            if hasattr(response, 'headers'):
                response.headers['X-RateLimit-Limit'] = str(info.get('limit', ''))
                response.headers['X-RateLimit-Remaining'] = str(info.get('remaining', ''))
                response.headers['X-RateLimit-Reset'] = str(int(info.get('reset_time', 0)))
                response.headers['X-RateLimit-Rule'] = info.get('rule', '')
            
            return response
        
        return wrapper
    return decorator


def get_client_ip():
    """Get the real client IP address, handling proxy scenarios"""
    # Check for X-Forwarded-For header (proxy scenarios)
    forwarded_for = request.headers.get('X-Forwarded-For')
    if forwarded_for:
        # X-Forwarded-For can contain multiple IPs: "client, proxy1, proxy2"
        # The first IP is typically the original client
        client_ip = forwarded_for.split(',')[0].strip()
        
        # Validate the IP address
        try:
            ipaddress.ip_address(client_ip)
            return client_ip
        except ipaddress.AddressValueError:
            # If invalid, fall back to other headers
            pass
    
    # Check other proxy headers
    real_ip = request.headers.get('X-Real-IP')
    if real_ip:
        try:
            ipaddress.ip_address(real_ip)
            return real_ip
        except ipaddress.AddressValueError:
            pass
    
    # Check CF-Connecting-IP (Cloudflare)
    cf_ip = request.headers.get('CF-Connecting-IP')
    if cf_ip:
        try:
            ipaddress.ip_address(cf_ip)
            return cf_ip
        except ipaddress.AddressValueError:
            pass
    
    # Fall back to remote_addr
    return request.remote_addr or 'unknown'


def rate_limit_by_ip():
    """Rate limit by IP address"""
    return get_client_ip()


def rate_limit_by_user():
    """Rate limit by authenticated user"""
    if hasattr(g, 'current_user') and g.current_user:
        return f"user:{getattr(g.current_user, 'id', 'anonymous')}"
    return get_client_ip()


def rate_limit_by_api_key():
    """Rate limit by API key"""
    api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
    if api_key:
        return f"api_key:{hashlib.sha256(api_key.encode()).hexdigest()[:16]}"
    return get_client_ip()


def is_admin_user():
    """Check if current user is admin (bypass condition)"""
    if hasattr(g, 'current_user') and g.current_user:
        return getattr(g.current_user, 'is_admin', False)
    return False


def is_internal_request():
    """Check if request is from internal network (bypass condition)"""
    ip = get_client_ip()
    if ip and ip != 'unknown':
        try:
            ip_obj = ipaddress.ip_address(ip)
            return ip_obj.is_private or ip_obj.is_loopback
        except ipaddress.AddressValueError:
            pass
    return False
