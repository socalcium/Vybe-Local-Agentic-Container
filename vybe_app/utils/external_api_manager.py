"""
External API Manager for Vybe Application
Provides circuit breaker pattern, retry logic, and comprehensive error handling
for all external service integrations.
"""

import time
import asyncio
import threading
from typing import Any, Dict, Optional, Callable, List
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..logger import log_info, log_warning, log_error


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit is open, requests fail fast
    HALF_OPEN = "half_open"  # Testing if service is back


@dataclass
class APIConfig:
    """Configuration for external API"""
    name: str
    base_url: str
    timeout: int = 30
    max_retries: int = 3
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: int = 60
    rate_limit_requests: int = 100
    rate_limit_window: int = 60


class CircuitBreaker:
    """Circuit breaker implementation for external APIs"""
    
    def __init__(self, threshold: int = 5, timeout: int = 60):
        self.threshold = threshold
        self.timeout = timeout
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.lock = threading.Lock()
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
            else:
                raise Exception(f"Circuit breaker is OPEN for {self.timeout} seconds")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e
    
    def _on_success(self):
        """Handle successful call"""
        with self.lock:
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.last_failure_time = None
    
    def _on_failure(self):
        """Handle failed call"""
        with self.lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.threshold:
                self.state = CircuitState.OPEN
                log_warning(f"Circuit breaker opened after {self.failure_count} failures")
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt reset"""
        if self.last_failure_time is None:
            return True
        return time.time() - self.last_failure_time >= self.timeout


class RateLimiter:
    """Rate limiter for API calls"""
    
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = []
        self.lock = threading.Lock()
    
    def can_proceed(self) -> bool:
        """Check if request can proceed"""
        with self.lock:
            now = time.time()
            # Remove old requests outside window
            self.requests = [req_time for req_time in self.requests 
                           if now - req_time < self.window_seconds]
            
            if len(self.requests) < self.max_requests:
                self.requests.append(now)
                return True
            return False
    
    def wait_if_needed(self):
        """Wait if rate limit is exceeded"""
        if not self.can_proceed():
            # Calculate exact wait time instead of busy waiting
            oldest_request = min(self.requests)
            wait_time = (oldest_request + self.window_seconds) - time.time()
            if wait_time > 0:
                time.sleep(wait_time)


class ExternalAPIManager:
    """Manages external API integrations with circuit breaker and rate limiting"""
    
    def __init__(self):
        self.apis: Dict[str, Dict[str, Any]] = {}
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """Create requests session with retry strategy"""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)  # type: ignore
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def register_api(self, config: APIConfig):
        """Register an external API"""
        self.apis[config.name] = {
            'config': config,
            'circuit_breaker': CircuitBreaker(
                config.circuit_breaker_threshold,
                config.circuit_breaker_timeout
            ),
            'rate_limiter': RateLimiter(
                config.rate_limit_requests,
                config.rate_limit_window
            ),
            'stats': {
                'total_requests': 0,
                'successful_requests': 0,
                'failed_requests': 0,
                'circuit_breaker_trips': 0
            }
        }
        log_info(f"Registered external API: {config.name}")
    
    def call_api(self, api_name: str, method: str = 'GET', 
                endpoint: str = '', data: Optional[Dict] = None, 
                headers: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
        """Make API call with circuit breaker and rate limiting"""
        if api_name not in self.apis:
            raise ValueError(f"API '{api_name}' not registered")
        
        api_info = self.apis[api_name]
        config = api_info['config']
        circuit_breaker = api_info['circuit_breaker']
        rate_limiter = api_info['rate_limiter']
        stats = api_info['stats']
        
        # Update stats
        stats['total_requests'] += 1
        
        # Check rate limit
        rate_limiter.wait_if_needed()
        
        # Prepare request
        url = f"{config.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        request_headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Vybe-AI-Application/1.0'
        }
        if headers:
            request_headers.update(headers)
        
        def make_request():
            """Make the actual HTTP request"""
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    json=data,
                    headers=request_headers,
                    timeout=config.timeout,
                    **kwargs
                )
                
                # Raise exception for bad status codes
                response.raise_for_status()
                
                return {
                    'success': True,
                    'data': response.json() if response.content else None,
                    'status_code': response.status_code,
                    'headers': dict(response.headers)
                }
                
            except requests.exceptions.RequestException as e:
                raise Exception(f"API request failed: {str(e)}")
        
        # Execute with circuit breaker
        try:
            result = circuit_breaker.call(make_request)
            stats['successful_requests'] += 1
            return result
            
        except Exception as e:
            stats['failed_requests'] += 1
            if circuit_breaker.state == CircuitState.OPEN:
                stats['circuit_breaker_trips'] += 1
            
            log_error(f"API call failed for {api_name}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'circuit_state': circuit_breaker.state.value
            }
    
    def get_api_status(self, api_name: str) -> Optional[Dict[str, Any]]:
        """Get status of registered API"""
        if api_name not in self.apis:
            return None
        
        api_info = self.apis[api_name]
        circuit_breaker = api_info['circuit_breaker']
        
        return {
            'name': api_name,
            'config': {
                'base_url': api_info['config'].base_url,
                'timeout': api_info['config'].timeout,
                'max_retries': api_info['config'].max_retries
            },
            'circuit_breaker': {
                'state': circuit_breaker.state.value,
                'failure_count': circuit_breaker.failure_count,
                'last_failure_time': circuit_breaker.last_failure_time
            },
            'stats': api_info['stats'].copy()
        }
    
    def get_all_status(self) -> Dict[str, Any]:
        """Get status of all registered APIs"""
        return {
            api_name: self.get_api_status(api_name)
            for api_name in self.apis.keys()
        }
    
    def reset_circuit_breaker(self, api_name: str) -> bool:
        """Manually reset circuit breaker for an API"""
        if api_name not in self.apis:
            return False
        
        api_info = self.apis[api_name]
        circuit_breaker = api_info['circuit_breaker']
        
        with circuit_breaker.lock:
            circuit_breaker.state = CircuitState.CLOSED
            circuit_breaker.failure_count = 0
            circuit_breaker.last_failure_time = None
        
        log_info(f"Reset circuit breaker for API: {api_name}")
        return True


# Global API manager instance
api_manager = ExternalAPIManager()


# Pre-configured API configurations
BRAVE_SEARCH_CONFIG = APIConfig(
    name="brave_search",
    base_url="https://api.search.brave.com",
    timeout=10,
    max_retries=2,
    circuit_breaker_threshold=3,
    circuit_breaker_timeout=30,
    rate_limit_requests=50,
    rate_limit_window=60
)

HOME_ASSISTANT_CONFIG = APIConfig(
    name="home_assistant",
    base_url="",  # Will be set dynamically
    timeout=15,
    max_retries=3,
    circuit_breaker_threshold=5,
    circuit_breaker_timeout=60,
    rate_limit_requests=100,
    rate_limit_window=60
)

GITHUB_API_CONFIG = APIConfig(
    name="github",
    base_url="https://api.github.com",
    timeout=20,
    max_retries=3,
    circuit_breaker_threshold=5,
    circuit_breaker_timeout=60,
    rate_limit_requests=30,
    rate_limit_window=60
)


def register_default_apis():
    """Register default external APIs"""
    api_manager.register_api(BRAVE_SEARCH_CONFIG)
    api_manager.register_api(GITHUB_API_CONFIG)
    log_info("Registered default external APIs")


def get_api_manager() -> ExternalAPIManager:
    """Get the global API manager instance"""
    return api_manager
